"""HTTP entry point: `workflow serve` (ADR-004, AC-01..AC-10; RF-1..RF-5).

Composition root, same category as `cli.py` — the only place besides `cli.py`
that imports concrete adapters and wires them into the application core.
Reuses `WorkflowEngine`/`FileSystemPluginRegistry`/`YamlJsonChainLoader`/
`SqliteStateStore` exactly as `run-many` (ADR-003): one thread per execution,
one SQLite file per `chain_name` under `--watch-dir`.

Monitoring (`GET /runs`/`GET /runs/{chain_name}`) reads `.db` files directly via
`sqlite3` (short-lived read connections), not through `StateStorePort` — this is
what lets it see executions started by `run`/`run-many` in a terminal, with no
coupling to who created them (ADR-004, Decisão).

Cancellation (`POST /runs/{chain_name}/cancelar`) only ever tracks executions this
process itself submitted (`ServerState.active`). It cannot kill an in-flight step:
each plugin's `subprocess.run` call is blocking and never hands its `Popen` back to
the caller, so there is no handle here to terminate — `cancel()` only succeeds for
work that hasn't started running yet (`Future.cancel()`, guaranteed by the stdlib).
See ADR-004, Consequências, for why this is a disclosed scope decision, not an
oversight.

`GET /runs/{chain_name}/stream` (SSE) and `POST /runs/{chain_name}/instrucoes`
(ADR-005) are different from cancellation in exactly this respect: they resolve
the currently-active `claude_code_runner` step purely from the `.db` file +
the chain's YAML config (`_resolve_active_claude_step`) — no dependency on
`ServerState.active` — and then tail/append a **file** at a deterministic path
(same convention as `session_log_path`, ADR-002). Because that mechanism is
file-based, it works identically whether the run was started by this `serve`
process, by `run`, or by `run-many` in a terminal (ADR-005, RNF-01).

`CORSMiddleware` (ADR-006, contexto `frontend`) is the only change made on this
module's behalf of the new frontend: permissive by decision (`allow_origins=["*"]`,
no credentials), consistent with "no authentication in this version" — not an
oversight. No route, payload, or error contract changes.

`GET /workflows`, `GET /workspace/repos` and `POST /runs/from-template` (ADR-007)
add a template-driven trigger path alongside the existing `POST /runs`, which is
unchanged: a template is a chain config file that also declares
`id`/`label`/`description`/`params_schema` (`FileSystemWorkflowTemplateRegistry`).
`POST /runs/from-template` validates the submitted params, materializes a real
chain YAML under `<watch_dir>/_generated-configs/`, and calls `ServerState.trigger`
— the exact same path `POST /runs` uses — so nothing about how a run is monitored,
streamed, or resumed needs to know it came from a template.

`archived` (ADR-011, contexto `frontend`, RF-03/RF-04) follows the same
`.db`-is-the-source-of-truth philosophy as `plugin` (ADR-010): `archived_at` is a
column on `workflow_runs`, added on demand by `_ensure_archived_column` (additive,
idempotent `ALTER TABLE`), read/written direct via `sqlite3` — never through
`StateStorePort`. `GET /runs` defaults to non-archived (today's behavior, preserved)
and accepts `?archived=true` for the archived-only view; `GET /runs/{chain_name}`
always reports `archived`. `POST /runs/{chain_name}/arquivar` and `.../desarquivar`
are idempotent and 404 exactly like `.../cancelar` for an unknown `chain_name`.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from collections.abc import Generator, Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from workflow_engine.adapters.filesystem_plugin_registry import FileSystemPluginRegistry
from workflow_engine.adapters.filesystem_workflow_template_registry import (
    FileSystemWorkflowTemplateRegistry,
)
from workflow_engine.adapters.json_event_logger import JsonEventLogger
from workflow_engine.adapters.sqlite_state_store import SqliteStateStore
from workflow_engine.adapters.yaml_json_chain_loader import YamlJsonChainLoader
from workflow_engine.application.workflow_engine import WorkflowEngine
from workflow_engine.application.workflow_templates import (
    materialize_chain_raw,
    validate_params,
)
from workflow_engine.domain.exceptions import (
    ChainValidationError,
    WorkflowFailed,
    WorkflowTemplateNotFoundError,
)


class RunRequest(BaseModel):
    config_path: str


class FromTemplateRequest(BaseModel):
    template_id: str
    params: dict = {}


class InstructionRequest(BaseModel):
    mensagem: str


@dataclass
class TrackedRun:
    future: Future
    config_path: str


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ServerState:
    """Everything `serve` needs across requests: registry, pool, and which
    executions *this process* has submitted (for cancel/already-running checks).
    """

    def __init__(
        self,
        plugins_dir: str,
        watch_dir: str,
        max_parallel: int,
        correlation_keys: frozenset[str],
        templates_dir: str = "./config/workflow_templates",
        local_repos_root: str | None = None,
    ):
        self.registry = FileSystemPluginRegistry(plugins_dir)
        self.registry.discover()
        self.watch_dir = Path(watch_dir)
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.correlation_keys = correlation_keys
        self.pool = ThreadPoolExecutor(max_workers=max_parallel)
        self._lock = threading.Lock()
        self.active: dict[str, TrackedRun] = {}
        self.local_repos_root = local_repos_root
        self.template_registry = FileSystemWorkflowTemplateRegistry(templates_dir)
        self.template_registry.discover()
        # ADR-007: materialized chain YAMLs live inside watch_dir, so a template
        # run is indistinguishable from any other run once triggered — same
        # `.db` file convention, same monitoring/stream/instructions endpoints.
        self.generated_configs_dir = self.watch_dir / "_generated-configs"
        self.generated_configs_dir.mkdir(parents=True, exist_ok=True)

    def db_path(self, chain_name: str) -> Path:
        return self.watch_dir / f"{chain_name}.db"

    def trigger_from_template(
        self, template_id: str, submitted: dict
    ) -> tuple[str | None, str | None]:
        """Returns (chain_name, error_code). error_code is None on success.

        Materializes a real chain YAML from the template + submitted params and
        delegates to `trigger()` — a template run goes through the exact same
        start path as `POST /runs`, so nothing downstream (monitoring, SSE
        stream, instructions) needs to distinguish how a run was started.
        """
        try:
            template = self.template_registry.get(template_id)
        except WorkflowTemplateNotFoundError:
            return None, "template_not_found"

        errors = validate_params(template, submitted)
        if errors:
            return None, "invalid_params"

        chain_name = f"{template_id}--{uuid.uuid4().hex[:8]}"
        raw = materialize_chain_raw(template, submitted, chain_name)
        config_path = self.generated_configs_dir / f"{chain_name}.yaml"
        config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        return self.trigger(str(config_path))

    def trigger(self, config_path: str) -> tuple[str | None, str | None]:
        """Returns (chain_name, error_code). error_code is None on success."""
        try:
            chain = YamlJsonChainLoader().load(config_path, known_plugins=self.registry.names())
        except ChainValidationError:
            return None, "invalid_config"

        with self._lock:
            existing = self.active.get(chain.name)
            if existing is not None and not existing.future.done():
                return chain.name, "already_running"
            future = self.pool.submit(self._run_one, config_path, chain)
            self.active[chain.name] = TrackedRun(future=future, config_path=config_path)
        return chain.name, None

    def _run_one(self, config_path: str, chain: Any) -> None:
        with SqliteStateStore(self.db_path(chain.name)) as state_store:
            engine = WorkflowEngine(
                self.registry,
                state_store,
                event_logger=JsonEventLogger(),
                correlation_keys=self.correlation_keys,
            )
            try:
                engine.run(chain, config_path)
            except WorkflowFailed:
                pass  # already persisted as failed by the Engine; nothing more to do

    def cancel(self, chain_name: str) -> str:
        """Returns "cancelled" | "already_running" | "not_cancellable" | "not_found"."""
        with self._lock:
            tracked = self.active.get(chain_name)
        if tracked is None:
            return "not_cancellable" if self.db_path(chain_name).exists() else "not_found"
        if tracked.future.cancel():
            return "cancelled"
        return "already_running" if not tracked.future.done() else "not_cancellable"


def _ensure_archived_column(db_file: Path) -> None:
    """Additive, idempotent migration (ADR-011-AC-01): adds `archived_at` to
    `workflow_runs` on demand, so both `.db` files created before and after this
    feature work with no separate migration step. `archived` is a monitoring-only
    concept (like `plugin` per step, ADR-010) — read/written direct via `sqlite3`,
    never through `StateStorePort` (keeps the ADR-004 decoupling: monitoring must see
    executions regardless of who/what created the `.db` file).
    """
    conn = sqlite3.connect(db_file)
    try:
        try:
            conn.execute("ALTER TABLE workflow_runs ADD COLUMN archived_at TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists — degrade gracefully, never fail the caller
    finally:
        conn.close()


def set_run_archived(watch_dir: Path, chain_name: str, archived: bool) -> bool:
    """Returns False if chain_name has no `.db` file (ADR-011-AC-04)."""
    db_file = watch_dir / f"{chain_name}.db"
    if not db_file.exists():
        return False
    _ensure_archived_column(db_file)
    conn = sqlite3.connect(db_file)
    try:
        conn.execute(
            "UPDATE workflow_runs SET archived_at = ? "
            "WHERE run_id = (SELECT run_id FROM workflow_runs ORDER BY created_at DESC LIMIT 1)",
            (_now() if archived else None,),
        )
        conn.commit()
    finally:
        conn.close()
    return True


def list_runs(watch_dir: Path, archived: bool = False) -> list[dict]:
    results = []
    for db_file in sorted(watch_dir.glob("*.db")):
        _ensure_archived_column(db_file)
        row = _query_one(
            db_file,
            "SELECT run_id, workflow_name, status, created_at, updated_at, archived_at "
            "FROM workflow_runs ORDER BY created_at DESC LIMIT 1",
        )
        if row is None:
            continue
        run_id, workflow_name, status, created_at, updated_at, archived_at = row
        if bool(archived_at) != archived:
            continue
        results.append(
            {
                "chain_name": db_file.stem,
                "run_id": run_id,
                "workflow_name": workflow_name,
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
                "duration_seconds": _duration_seconds(status, created_at, updated_at),
                "source_db": db_file.name,
                "archived": bool(archived_at),
            }
        )
    return results


def _duration_seconds(status: str, created_at: str, updated_at: str) -> int | None:
    """Deriva a duração de uma execução dos timestamps já persistidos (ADR-012),
    sem nenhuma nova coluna/instrumentação. Para status terminal, `updated_at` foi
    escrito exatamente na transição final, então a diferença é fixa; para
    `running`/`pending`, `updated_at` fica parado no último step concluído, então
    usamos `now()` para refletir o tempo decorrido até o momento da consulta.
    """
    try:
        start = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return None
    if status in ("running", "pending"):
        end = datetime.now(timezone.utc)
    else:
        try:
            end = datetime.fromisoformat(updated_at)
        except (TypeError, ValueError):
            return None
    return max(0, round((end - start).total_seconds()))


def _step_plugins_by_name(config_path: str) -> dict[str, str]:
    """Maps step_name -> plugin from the chain's own YAML config, reloaded fresh
    (ADR-010, AT-05) — same technique already used by `_resolve_active_claude_step`
    (ADR-005) to decide whether a step is streamable. Returns {} (never raises) if
    the config can't be reloaded, so a missing/invalid file degrades to `plugin:
    null` per step instead of failing the whole run-detail response.
    """
    try:
        chain = YamlJsonChainLoader().load(config_path)
    except ChainValidationError:
        return {}
    return {step.name: step.plugin for step in chain.steps}


def get_run_detail(watch_dir: Path, chain_name: str, include_io: bool) -> dict | None:
    db_file = watch_dir / f"{chain_name}.db"
    if not db_file.exists():
        return None
    _ensure_archived_column(db_file)
    run_row = _query_one(
        db_file,
        "SELECT run_id, status, created_at, updated_at, config_path, archived_at "
        "FROM workflow_runs ORDER BY created_at DESC LIMIT 1",
    )
    if run_row is None:
        return None
    run_id, status, created_at, updated_at, config_path, archived_at = run_row
    plugins_by_step = _step_plugins_by_name(config_path)

    columns = "step_name, status, attempt_count, started_at, finished_at, error_message"
    if include_io:
        columns += ", input, output"
    step_rows = _query_all(
        db_file,
        f"SELECT {columns} FROM step_executions WHERE run_id = ? ORDER BY started_at",
        (run_id,),
    )
    steps = []
    for r in step_rows:
        step = {
            "step_name": r[0],
            "status": r[1],
            "attempt_count": r[2],
            "started_at": r[3],
            "finished_at": r[4],
            "error_message": r[5],
            "plugin": plugins_by_step.get(r[0]),
        }
        if include_io:
            step["input"] = json.loads(r[6]) if r[6] else None
            step["output"] = json.loads(r[7]) if r[7] else None
        steps.append(step)

    return {
        "chain_name": chain_name,
        "run_id": run_id,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "duration_seconds": _duration_seconds(status, created_at, updated_at),
        "steps": steps,
        "archived": bool(archived_at),
    }


def _query_one(db_file: Path, sql: str, params: Iterable[Any] = ()) -> tuple | None:
    conn = sqlite3.connect(db_file)
    try:
        return conn.execute(sql, tuple(params)).fetchone()
    finally:
        conn.close()


def _query_all(db_file: Path, sql: str, params: Iterable[Any] = ()) -> list[tuple]:
    conn = sqlite3.connect(db_file)
    try:
        return conn.execute(sql, tuple(params)).fetchall()
    finally:
        conn.close()


def _session_log_path(workspace_path: str, run_id: str, step_name: str) -> Path:
    # Same deterministic convention as plugins/claude_code_runner.py (ADR-002) —
    # duplicated rather than imported, since adapters/ never depends on plugins/
    # (plugins are externally discovered, not a core import).
    return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.log"


def _instructions_path(workspace_path: str, run_id: str, step_name: str) -> Path:
    return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.instrucoes.jsonl"


def _resolve_active_claude_step(watch_dir: Path, chain_name: str) -> tuple[str, str, str] | None:
    """Returns (workspace_path, run_id, step_name) for chain_name's currently
    "running" step, if — and only if — that step's plugin is
    `claude_code_runner` (per the chain's own YAML config, reloaded fresh here;
    ADR-005, AT-04). Returns None for every other case: unknown chain_name, no
    running step, or a running step that isn't a Claude Code Runner — all
    collapse to the same "not streamable/interactable right now" outcome
    (ADR-005, AC-07/AC-09).
    """
    db_file = watch_dir / f"{chain_name}.db"
    if not db_file.exists():
        return None
    run_row = _query_one(
        db_file, "SELECT run_id, config_path FROM workflow_runs ORDER BY created_at DESC LIMIT 1"
    )
    if run_row is None:
        return None
    run_id, config_path = run_row

    running_row = _query_one(
        db_file,
        "SELECT step_name, input FROM step_executions WHERE run_id = ? AND status = 'running'",
        (run_id,),
    )
    if running_row is None:
        return None
    step_name, input_json = running_row

    try:
        # No known_plugins passed: we only need the step->plugin mapping here,
        # not full validation against a live registry.
        chain = YamlJsonChainLoader().load(config_path)
    except ChainValidationError:
        return None
    step_def = next((s for s in chain.steps if s.name == step_name), None)
    if step_def is None or step_def.plugin != "claude_code_runner":
        return None

    input_data = json.loads(input_json) if input_json else {}
    workspace_path = input_data.get("workspace_path") if isinstance(input_data, dict) else None
    if not workspace_path:
        # ADR-007: the `investigar` modo has no preceding workspace_setup step, so
        # there is no carry-forward input — workspace_path lives in the step's own
        # params instead (same fallback order as claude_code_runner.py itself).
        # Found running the investigar modo for real against a live SSE stream.
        workspace_path = step_def.params.get("workspace_path")
    if not workspace_path:
        return None
    return workspace_path, run_id, step_name


def _tail_session_log(
    db_file: Path, run_id: str, step_name: str, log_path: Path, poll_interval: float = 0.2
) -> Generator[str, None, None]:
    """Yields SSE `data:` frames for each line already in log_path, then keeps
    polling for new ones (ADR-005, AC-06) until the step's own status stops
    being "running" (ADR-001 State Store — same file the plugin itself writes
    to), draining whatever landed in the gap before stopping.
    """
    with open(log_path, encoding="utf-8") as f:
        while True:
            line = f.readline()
            if line:
                yield f"data: {line.rstrip(chr(10))}\n\n"
                continue
            status_row = _query_one(
                db_file,
                "SELECT status FROM step_executions WHERE run_id = ? AND step_name = ?",
                (run_id, step_name),
            )
            if status_row is None or status_row[0] != "running":
                for remaining_line in f.read().splitlines():
                    yield f"data: {remaining_line}\n\n"
                return
            time.sleep(poll_interval)


def build_app(
    plugins_dir: str = "./plugins",
    watch_dir: str = "./run-many-state",
    max_parallel: int = 3,
    correlation_keys: frozenset[str] = frozenset(),
    templates_dir: str = "./config/workflow_templates",
    local_repos_root: str | None = None,
) -> FastAPI:
    state = ServerState(
        plugins_dir,
        watch_dir,
        max_parallel,
        correlation_keys,
        templates_dir=templates_dir,
        local_repos_root=local_repos_root,
    )
    app = FastAPI(title="workflow_engine serve")
    app.state.server = state

    # ADR-006, AT-06: habilita o frontend (dev server em outra origem) a chamar esta
    # API. Sem credenciais (RNF-01, sem autenticação nesta versão) — permissivo por
    # decisão explícita, não descuido; ver ADR-006, Riscos.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(HTTPException)
    def _flat_error(request: Request, exc: HTTPException) -> JSONResponse:
        # FastAPI's default handler wraps `detail` as {"detail": <detail>}; the ADR-004
        # contract is a flat {"error": {"code", "message"}} body, so `detail` (already
        # built by `_error()`) is returned as-is instead of re-wrapped.
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.post("/runs", status_code=202)
    def create_run(body: RunRequest) -> dict:
        chain_name, error = state.trigger(body.config_path)
        if error == "invalid_config":
            raise HTTPException(
                400, detail=_error("invalid_config", f"invalid config: {body.config_path}")
            )
        if error == "already_running":
            raise HTTPException(
                409, detail=_error("already_running", f"'{chain_name}' is already running")
            )
        return {"chain_name": chain_name, "status": "started"}

    @app.get("/workflows")
    def get_workflows() -> list[dict]:
        return [
            {
                "id": t.id,
                "label": t.label,
                "description": t.description,
                "params_schema": [
                    {
                        "name": p.name,
                        "label": p.label,
                        "type": p.type,
                        "required": p.required,
                        "source": p.source,
                    }
                    for p in t.params
                ],
            }
            for t in state.template_registry.list()
        ]

    @app.get("/workspace/repos")
    def get_local_repos(root: str | None = None) -> list[dict]:
        # ADR-009 (AC-06): `root` troca a raiz listada sem reiniciar o processo. É um
        # filtro de leitura, não estado do motor — o disparo usa o `repo_path` completo
        # que chega no parâmetro do template. Ausente, vale a raiz do serve (ADR-007).
        configured = root or state.local_repos_root
        if not configured:
            return []
        base = Path(configured)
        if not base.is_dir():
            return []
        return [{"name": p.name, "path": str(p)} for p in sorted(base.iterdir()) if p.is_dir()]

    @app.post("/runs/from-template", status_code=202)
    def create_run_from_template(body: FromTemplateRequest) -> dict:
        chain_name, error = state.trigger_from_template(body.template_id, body.params)
        if error == "template_not_found":
            raise HTTPException(
                404, detail=_error("template_not_found", f"unknown template_id: {body.template_id}")
            )
        if error == "invalid_params":
            raise HTTPException(
                400,
                detail=_error(
                    "invalid_params", f"missing required params for '{body.template_id}'"
                ),
            )
        if error == "already_running":
            raise HTTPException(
                409, detail=_error("already_running", f"'{chain_name}' is already running")
            )
        return {"chain_name": chain_name, "status": "started"}

    @app.get("/runs")
    def get_runs(archived: str | None = None) -> list[dict]:
        # ADR-011-AC-06: sem o parâmetro (ou qualquer valor != "true"), retorna só
        # não-arquivadas — comportamento de hoje, preservado.
        return list_runs(state.watch_dir, archived=(archived == "true"))

    @app.get("/runs/{chain_name}")
    def get_run(chain_name: str, include: str | None = Query(default=None)) -> dict:
        detail = get_run_detail(state.watch_dir, chain_name, include_io=(include == "io"))
        if detail is None:
            raise HTTPException(
                404, detail=_error("not_found", f"unknown chain_name: {chain_name}")
            )
        return detail

    @app.get("/runs/{chain_name}/stream")
    def stream_run(chain_name: str) -> StreamingResponse:
        resolved = _resolve_active_claude_step(state.watch_dir, chain_name)
        if resolved is None:
            raise HTTPException(
                409,
                detail=_error(
                    "not_streamable",
                    f"no active claude_code_runner step for '{chain_name}'",
                ),
            )
        workspace_path, run_id, step_name = resolved
        log_path = _session_log_path(workspace_path, run_id, step_name)
        if not log_path.exists():
            raise HTTPException(
                409, detail=_error("not_streamable", "session log not yet available")
            )
        db_file = state.watch_dir / f"{chain_name}.db"
        return StreamingResponse(
            _tail_session_log(db_file, run_id, step_name, log_path),
            media_type="text/event-stream",
        )

    @app.post("/runs/{chain_name}/instrucoes", status_code=202)
    def post_instruction(chain_name: str, body: InstructionRequest) -> dict:
        resolved = _resolve_active_claude_step(state.watch_dir, chain_name)
        if resolved is None:
            raise HTTPException(
                409,
                detail=_error(
                    "not_interactable",
                    f"no active claude_code_runner step for '{chain_name}'",
                ),
            )
        workspace_path, run_id, step_name = resolved
        instructions_path = _instructions_path(workspace_path, run_id, step_name)
        instructions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(instructions_path, "a", encoding="utf-8") as f:
            f.write(body.mensagem + "\n")
        return {"chain_name": chain_name, "status": "accepted"}

    @app.post("/runs/{chain_name}/cancelar")
    def cancel_run(chain_name: str) -> dict:
        outcome = state.cancel(chain_name)
        if outcome == "cancelled":
            return {"chain_name": chain_name, "status": "cancelled"}
        if outcome == "already_running":
            raise HTTPException(
                409,
                detail=_error(
                    "already_running",
                    f"'{chain_name}' step is already running — cancelling an in-flight "
                    "step is not supported in this version",
                ),
            )
        if outcome == "not_cancellable":
            raise HTTPException(
                409,
                detail=_error(
                    "not_cancellable",
                    f"'{chain_name}' was not started by this server — interrupt the "
                    "process that started it instead",
                ),
            )
        raise HTTPException(404, detail=_error("not_found", f"unknown chain_name: {chain_name}"))

    @app.post("/runs/{chain_name}/arquivar")
    def archive_run(chain_name: str) -> dict:
        if not set_run_archived(state.watch_dir, chain_name, archived=True):
            raise HTTPException(
                404, detail=_error("not_found", f"unknown chain_name: {chain_name}")
            )
        return {"chain_name": chain_name, "archived": True}

    @app.post("/runs/{chain_name}/desarquivar")
    def unarchive_run(chain_name: str) -> dict:
        if not set_run_archived(state.watch_dir, chain_name, archived=False):
            raise HTTPException(
                404, detail=_error("not_found", f"unknown chain_name: {chain_name}")
            )
        return {"chain_name": chain_name, "archived": False}

    return app


def cmd_serve(args) -> int:
    import uvicorn

    correlation_keys = frozenset(
        key.strip() for key in args.correlation_keys.split(",") if key.strip()
    )
    app = build_app(
        plugins_dir=args.plugins_dir,
        watch_dir=args.watch_dir,
        max_parallel=args.max_parallel,
        correlation_keys=correlation_keys,
        templates_dir=args.workflow_templates_dir,
        local_repos_root=args.local_repos_root,
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port)
    return 0
