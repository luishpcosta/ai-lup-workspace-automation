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
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from workflow_engine.adapters.filesystem_plugin_registry import FileSystemPluginRegistry
from workflow_engine.adapters.json_event_logger import JsonEventLogger
from workflow_engine.adapters.sqlite_state_store import SqliteStateStore
from workflow_engine.adapters.yaml_json_chain_loader import YamlJsonChainLoader
from workflow_engine.application.workflow_engine import WorkflowEngine
from workflow_engine.domain.exceptions import ChainValidationError, WorkflowFailed


class RunRequest(BaseModel):
    config_path: str


@dataclass
class TrackedRun:
    future: Future
    config_path: str


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


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
    ):
        self.registry = FileSystemPluginRegistry(plugins_dir)
        self.registry.discover()
        self.watch_dir = Path(watch_dir)
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.correlation_keys = correlation_keys
        self.pool = ThreadPoolExecutor(max_workers=max_parallel)
        self._lock = threading.Lock()
        self.active: dict[str, TrackedRun] = {}

    def db_path(self, chain_name: str) -> Path:
        return self.watch_dir / f"{chain_name}.db"

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


def list_runs(watch_dir: Path) -> list[dict]:
    results = []
    for db_file in sorted(watch_dir.glob("*.db")):
        row = _query_one(
            db_file,
            "SELECT run_id, workflow_name, status, created_at, updated_at "
            "FROM workflow_runs ORDER BY created_at DESC LIMIT 1",
        )
        if row is None:
            continue
        run_id, workflow_name, status, created_at, updated_at = row
        results.append(
            {
                "chain_name": db_file.stem,
                "run_id": run_id,
                "workflow_name": workflow_name,
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
                "source_db": db_file.name,
            }
        )
    return results


def get_run_detail(watch_dir: Path, chain_name: str, include_io: bool) -> dict | None:
    db_file = watch_dir / f"{chain_name}.db"
    if not db_file.exists():
        return None
    run_row = _query_one(
        db_file,
        "SELECT run_id, status, created_at, updated_at "
        "FROM workflow_runs ORDER BY created_at DESC LIMIT 1",
    )
    if run_row is None:
        return None
    run_id, status, created_at, updated_at = run_row

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
        "steps": steps,
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


def build_app(
    plugins_dir: str = "./plugins",
    watch_dir: str = "./run-many-state",
    max_parallel: int = 3,
    correlation_keys: frozenset[str] = frozenset(),
) -> FastAPI:
    state = ServerState(plugins_dir, watch_dir, max_parallel, correlation_keys)
    app = FastAPI(title="workflow_engine serve")
    app.state.server = state

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

    @app.get("/runs")
    def get_runs() -> list[dict]:
        return list_runs(state.watch_dir)

    @app.get("/runs/{chain_name}")
    def get_run(chain_name: str, include: str | None = Query(default=None)) -> dict:
        detail = get_run_detail(state.watch_dir, chain_name, include_io=(include == "io"))
        if detail is None:
            raise HTTPException(
                404, detail=_error("not_found", f"unknown chain_name: {chain_name}")
            )
        return detail

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
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port)
    return 0
