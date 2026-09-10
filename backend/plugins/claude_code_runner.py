"""Claude Code Runner plugin (ADR-002, AT-02/AT-03; ADR-005, AT-01..AT-03; ADR-007, AT-04).

Invokes the `claude` CLI as a **long-lived process** (`Popen`, stdin/stdout kept
open) using `--input-format stream-json --output-format stream-json --verbose`,
parametrized by `params.modo` (`"coding"`, `"review"`, `"investigar"`,
`"coding_local"` or `"coding_local_interativo"`). This replaced the ADR-002
one-shot `subprocess.run(capture_output=True)` invocation — the plugin's
external contract (`params`/`output`, `TransientError` semantics) is unchanged.

`coding_local_interativo` is `coding_local` (ADR-008) plus a real pause/resume
mechanism: the agent gets an extra `ask_user` MCP tool (`_build_interactive_mcp_config`,
`mcp_servers/ask_user_server.py`) it can call to block on a genuine human answer
mid-session — the `instructions_path` file below is fire-and-forget steering, not
a guaranteed pause, which is why this uses a tool call instead.

Everything below is verified against a real, live `claude` invocation this
session (`claude 2.1.260`), not assumed — see `adr/ADR-005-stream-interacao-agente.md`:

- `--mcp-config <path> --strict-mcp-config`: same as ADR-002 — never relies on
  project auto-discovered `.mcp.json`.
- `--output-format json --json-schema <schema>` in ADR-002 became
  `--output-format stream-json` here; the initial prompt is sent as the first
  stdin line (`{"type":"user","message":{"role":"user","content":...}}`), not a
  CLI positional argument — `--input-format stream-json` reads the whole
  conversation from stdin, not from argv.
- `--verbose` is *required* alongside `--output-format stream-json` in `--print`
  mode (the CLI errors otherwise).
- The final `type:"result"` event, when `--json-schema` is set, carries the
  schema-conforming payload twice: `result` (JSON-encoded string, as in ADR-002)
  and a new `structured_output` field — already a parsed object. `_extract_structured`
  prefers `structured_output`.
- Verified live: writing a **second** stdin message while the first is still
  being processed genuinely steers the agent mid-session (tested: "count slowly
  to 5" interrupted by "stop, just say X" — the agent actually stopped and
  complied). This is what `_poll_instructions` automates.
- Closing stdin (no more messages) is what ends the process — a stream-json
  session does not self-terminate after one turn. `_run_streaming_session`
  closes stdin as soon as it sees the `result` event for the current turn.

`session_log_path` (deterministic, `<workspace_path>/.workflow-logs/<run_id>/
<step_name>.log`, from ADR-002) is now written **incrementally** — one line per
event received — instead of only in a `finally` block, so the ADR-005 SSE
endpoint (`http_api.py`, `GET /runs/{chain_name}/stream`) can `tail -f` it live.
It is still guaranteed to exist even on failure, for the same reason as before:
this contract survives exceptions because it's a deterministic path, not
something only present in a successful `output`.

A sibling file, `<step_name>.instrucoes.jsonl` (also a deterministic path, same
directory), is polled by a background thread for new lines while the session is
active; each new line is forwarded to the live process's stdin as a user
message (ADR-005, RF-03). `POST /runs/{chain_name}/instrucoes` (http_api.py)
just appends to this file — the mechanism is file-based, not in-memory, so it
works the same whether the run was started by `serve`, `run`, or `run-many`
(ADR-005, RNF-01).
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError

_CODING_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "docs_referenced": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "docs_referenced"],
}

_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}

_INVESTIGAR_SCHEMA = {
    "type": "object",
    "properties": {
        "relatorio": {"type": "string"},
        "docs_consultados": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["relatorio", "docs_consultados"],
}

_CODING_LOCAL_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "docs_referenced": {"type": "array", "items": {"type": "string"}},
        "branch": {"type": "string"},
    },
    "required": ["summary", "docs_referenced", "branch"],
}

#: exit-code!=0 whose output matches one of these is treated as retriable;
#: anything else is a permanent failure.
_TRANSIENT_PATTERNS = ("rate_limit", "econnreset", "timeout", "network", "overloaded")

#: how often the instructions-file poller checks for new content (ADR-005, AC-04).
_DEFAULT_INSTRUCTION_POLL_INTERVAL = 0.2

#: how long to wait for the process to exit after we close its stdin, before
#: giving up and killing it — a stream-json session should wrap up quickly once
#: it knows no more input is coming.
_SHUTDOWN_TIMEOUT_SECONDS = 30


class ClaudeCodeRunnerPlugin(Plugin):
    def __init__(
        self,
        popen_factory=subprocess.Popen,
        claude_bin: str = "claude",
        instruction_poll_interval: float = _DEFAULT_INSTRUCTION_POLL_INTERVAL,
    ):
        self._popen_factory = popen_factory
        self._claude_bin = claude_bin
        self._instruction_poll_interval = instruction_poll_interval

    def run(self, context: PluginContext) -> Any:
        modo = context.params.get("modo")
        if modo == "coding":
            return self._run_coding(context)
        if modo == "review":
            return self._run_review(context)
        if modo == "investigar":
            return self._run_investigar(context)
        if modo == "coding_local":
            return self._run_coding_local(context)
        if modo == "coding_local_interativo":
            return self._run_coding_local_interativo(context)
        raise ValueError(f"claude_code_runner: invalid modo {modo!r}")

    # -- modo coding (ADR-002-AT-02, AC-04/AC-05) ---------------------------

    def _run_coding(self, context: PluginContext) -> dict:
        params = context.params
        input_data = context.input if isinstance(context.input, dict) else {}
        workdir = input_data.get("workspace_path") or params.get("workdir")
        if not workdir:
            raise ValueError(
                "claude_code_runner (coding): no workspace_path in context.input "
                "(expected from the Workspace Setup step via usa_output_anterior)"
            )
        historia_id = params["historia_id"]
        mcp_config_path = params["mcp_config_path"]

        log_path = self._session_log_path(workdir, context.run_id, context.step_name)
        instructions_path = self._instructions_path(workdir, context.run_id, context.step_name)
        cmd = self._build_cmd(mcp_config_path, _CODING_SCHEMA)
        prompt = self._coding_prompt(historia_id)

        returncode, lines = self._run_streaming_session(
            cmd, workdir, log_path, instructions_path, prompt
        )
        self._raise_if_failed(returncode, lines, log_path)
        result = self._extract_structured(self._find_result_event(lines), log_path)

        return {
            **input_data,
            "status": "success",
            "summary": result.get("summary", ""),
            "docs_referenced": result.get("docs_referenced", []),
            "session_log_path": str(log_path),
        }

    def _coding_prompt(self, historia_id: str) -> str:
        return (
            f"Implemente a história {historia_id}. Busque a história e a "
            "documentação relacionada (ADR/AC/PRD) que julgar necessária via MCP. "
            "Siga o SDD instalado neste repositório. Depois de implementar e "
            "verificar (rode os testes existentes), faça `git commit` das mudanças "
            f"com uma mensagem referenciando {historia_id}, e `git push` a branch "
            "atual para o remoto `origin` (a etapa seguinte da cadeia abre uma PR a "
            "partir dessa branch e precisa que ela já esteja no remoto — sem isso a "
            "etapa seguinte falha). Ao final, retorne um JSON com 'summary' (resumo "
            "do que foi feito) e 'docs_referenced' (lista dos ids de ADR/AC/PRD "
            "efetivamente consultados)."
        )

    # -- modo review (ADR-002-AT-03, AC-06/AC-07/AC-08) ----------------------

    def _run_review(self, context: PluginContext) -> dict:
        params = context.params
        input_data = context.input if isinstance(context.input, dict) else {}
        workdir = input_data.get("workspace_path") or params.get("workdir")
        if not workdir:
            raise ValueError(
                "claude_code_runner (review): no workspace_path in context.input "
                "(expected to have been carried forward through Git/PR and "
                "Shell/Script Runner)"
            )
        skill = params["skill"]
        pr_ref = params.get("pr_number") or input_data.get("pr_number")
        pr_ref = pr_ref or params.get("pr_url") or input_data.get("pr_url")
        if not pr_ref:
            raise ValueError("claude_code_runner (review): no pr_number/pr_url available")
        mcp_config_path = params["mcp_config_path"]

        log_path = self._session_log_path(workdir, context.run_id, context.step_name)
        instructions_path = self._instructions_path(workdir, context.run_id, context.step_name)
        cmd = self._build_cmd(mcp_config_path, _REVIEW_SCHEMA)
        prompt = self._review_prompt(skill, pr_ref)

        returncode, lines = self._run_streaming_session(
            cmd, workdir, log_path, instructions_path, prompt
        )
        self._raise_if_failed(returncode, lines, log_path)
        result = self._extract_structured(self._find_result_event(lines), log_path)

        return {
            "status": "success",
            "summary": result.get("summary", ""),
            "session_log_path": str(log_path),
        }

    def _review_prompt(self, skill: str, pr_ref: Any) -> str:
        return (
            f"Revise a mudança da PR {pr_ref} usando a skill {skill}. Ao final, "
            "retorne um JSON com 'summary' (resumo da revisão)."
        )

    # -- modo investigar (ADR-007, AT-04) ------------------------------------

    def _run_investigar(self, context: PluginContext) -> dict:
        """Read-only investigation: given a free-text prompt and (optionally)
        which docs to consult, investigate impact in an existing local
        checkout — no branch, no commit, no PR. Unlike `coding`/`review`, this
        mode has no preceding `workspace_setup` step in its chain (ADR-007,
        Decisão): `workspace_path` is expected in `params`, not carried forward
        via `context.input` — though `context.input` still wins if present, for
        consistency with the other modes.
        """
        params = context.params
        input_data = context.input if isinstance(context.input, dict) else {}
        workdir = input_data.get("workspace_path") or params.get("workspace_path")
        if not workdir:
            raise ValueError(
                "claude_code_runner (investigar): no workspace_path in context.input "
                "or context.params"
            )
        prompt_text = params["prompt"]
        docs_referenced = params.get("docs_referenced") or []
        mcp_config_path = params["mcp_config_path"]

        log_path = self._session_log_path(workdir, context.run_id, context.step_name)
        instructions_path = self._instructions_path(workdir, context.run_id, context.step_name)
        cmd = self._build_cmd(mcp_config_path, _INVESTIGAR_SCHEMA)
        prompt = self._investigar_prompt(prompt_text, docs_referenced)

        returncode, lines = self._run_streaming_session(
            cmd, workdir, log_path, instructions_path, prompt
        )
        self._raise_if_failed(returncode, lines, log_path)
        result = self._extract_structured(self._find_result_event(lines), log_path)

        return {
            "status": "success",
            "relatorio": result.get("relatorio", ""),
            "docs_consultados": result.get("docs_consultados", []),
            "session_log_path": str(log_path),
        }

    def _investigar_prompt(self, prompt_text: str, docs_referenced: list) -> str:
        docs_hint = (
            f" Consulte especificamente, via MCP, os documentos: {', '.join(docs_referenced)}."
            if docs_referenced
            else ""
        )
        return (
            f"{prompt_text}{docs_hint} Esta é uma investigação somente-leitura: não "
            "crie branch, não faça commit/push, não abra PR. Ao final, retorne um "
            "JSON com 'relatorio' (texto da análise/impacto encontrado) e "
            "'docs_consultados' (lista dos ids de documentos efetivamente consultados "
            "via MCP)."
        )

    # -- modo coding_local (ADR-008, AT-01) ----------------------------------

    def _run_coding_local(self, context: PluginContext) -> dict:
        """Implements against an already-existing local checkout — no preceding
        `workspace_setup` step (no clone, no branch created by the motor): the
        target repo's own git workflow decides branch naming, and the agent is
        the one who creates/pushes it, so the motor learns the branch name only
        from the agent's own structured output (`branch`, ADR-008 Decisão).
        Unlike `coding`, this never opens a PR itself — a downstream `git_pr`
        `confirm_pr` step (not `create_pr`) verifies the target repo's own CI
        opened one.
        """
        params = context.params
        input_data = context.input if isinstance(context.input, dict) else {}
        workdir = input_data.get("workspace_path") or params.get("workspace_path")
        if not workdir:
            raise ValueError(
                "claude_code_runner (coding_local): no workspace_path in context.input "
                "or context.params"
            )
        prompt_text = params["prompt"]
        docs_referenced = params.get("docs_referenced") or []
        mcp_config_path = params["mcp_config_path"]

        log_path = self._session_log_path(workdir, context.run_id, context.step_name)
        instructions_path = self._instructions_path(workdir, context.run_id, context.step_name)
        cmd = self._build_cmd(mcp_config_path, _CODING_LOCAL_SCHEMA)
        prompt = self._coding_local_prompt(prompt_text, docs_referenced)

        returncode, lines = self._run_streaming_session(
            cmd, workdir, log_path, instructions_path, prompt
        )
        self._raise_if_failed(returncode, lines, log_path)
        result = self._extract_structured(self._find_result_event(lines), log_path)

        return {
            "status": "success",
            "summary": result.get("summary", ""),
            "docs_referenced": result.get("docs_referenced", []),
            "branch": result.get("branch", ""),
            "workspace_path": str(workdir),
            "session_log_path": str(log_path),
        }

    def _coding_local_prompt(self, prompt_text: str, docs_referenced: list) -> str:
        docs_hint = (
            f" Consulte especificamente, via MCP, os documentos: {', '.join(docs_referenced)}."
            if docs_referenced
            else ""
        )
        return (
            f"Implemente: {prompt_text}{docs_hint} Este repositório já tem seu próprio "
            "fluxo de Git documentado (leia o CLAUDE.md/README relevante antes de "
            "começar, especialmente qualquer seção sobre fluxo de Git) — siga "
            "exatamente esse fluxo: nunca dê push direto na branch principal; "
            "crie (ou troque para) a branch apropriada segundo a convenção desse "
            "repositório. Depois de implementar e verificar (rode a verificação "
            "própria do repositório), faça `git commit` das mudanças e `git push` "
            "dessa branch para o remoto `origin`. Não abra a Pull Request você "
            "mesmo — este repositório já abre a PR automaticamente por conta "
            "própria depois do push; sua responsabilidade termina no push. Ao "
            "final, retorne um JSON com 'summary' (resumo do que foi feito), "
            "'docs_referenced' (ids de documentos efetivamente consultados) e "
            "'branch' (nome exato da branch para a qual você deu push)."
        )

    # -- modo coding_local_interativo (Q&A em tempo real via tool MCP ask_user) --

    def _run_coding_local_interativo(self, context: PluginContext) -> dict:
        """Same as `coding_local` (ADR-008) — local checkout already existing,
        no workspace_setup, agent follows the target repo's own Git flow and
        never opens the PR itself — except the agent additionally has an
        `ask_user` MCP tool available (`_build_interactive_mcp_config`) to pause
        and ask the human operator a question mid-session, via a call that
        genuinely blocks (tool-use protocol, not a prompt convention). The pause
        itself lives entirely inside the `ask_user` MCP server process
        (`mcp_servers/ask_user_server.py`), invisible to this plugin's own read
        loop, which keeps blocking on `proc.stdout` exactly as it already does
        for any other tool call — the one thing this modo does pass down to
        `_run_streaming_session` is `pergunta_path`, so `_poll_instructions`
        holds off forwarding a stray `/instrucoes` line into stdin while that
        tool call is outstanding (ADR-013).
        """
        params = context.params
        input_data = context.input if isinstance(context.input, dict) else {}
        workdir = input_data.get("workspace_path") or params.get("workspace_path")
        if not workdir:
            raise ValueError(
                "claude_code_runner (coding_local_interativo): no workspace_path in "
                "context.input or context.params"
            )
        prompt_text = params["prompt"]
        docs_referenced = params.get("docs_referenced") or []
        mcp_config_path = params["mcp_config_path"]

        log_path = self._session_log_path(workdir, context.run_id, context.step_name)
        instructions_path = self._instructions_path(workdir, context.run_id, context.step_name)
        pergunta_path = self._pergunta_path(workdir, context.run_id, context.step_name)
        interactive_mcp_config_path = self._build_interactive_mcp_config(
            mcp_config_path, workdir, context.run_id, context.step_name
        )
        cmd = self._build_cmd(interactive_mcp_config_path, _CODING_LOCAL_SCHEMA)
        prompt = self._coding_local_interativo_prompt(prompt_text, docs_referenced)

        returncode, lines = self._run_streaming_session(
            cmd, workdir, log_path, instructions_path, prompt, pergunta_path=pergunta_path
        )
        self._raise_if_failed(returncode, lines, log_path)
        result = self._extract_structured(self._find_result_event(lines), log_path)

        return {
            "status": "success",
            "summary": result.get("summary", ""),
            "docs_referenced": result.get("docs_referenced", []),
            "branch": result.get("branch", ""),
            "workspace_path": str(workdir),
            "session_log_path": str(log_path),
        }

    def _coding_local_interativo_prompt(self, prompt_text: str, docs_referenced: list) -> str:
        base = self._coding_local_prompt(prompt_text, docs_referenced)
        return (
            f"{base} Você tem disponível a tool 'ask_user': use-a sempre que "
            "precisar de uma decisão ou esclarecimento que não pode inferir com "
            "segurança sozinho (ex.: instrução ambígua, escolha entre abordagens "
            "de implementação, confirmação antes de algo difícil de reverter) — "
            "ela pausa a execução e espera uma resposta real do usuário pelo "
            "painel; não invente uma resposta no lugar de perguntar quando "
            "houver ambiguidade real."
        )

    # -- shared plumbing -------------------------------------------------

    def _build_cmd(self, mcp_config_path: str, schema: dict) -> list[str]:
        # Deliberately no -r/--resume, -c/--continue or --fork-session: every
        # call is a fresh session/context window (verified live — see module
        # docstring). No positional prompt either: --input-format stream-json
        # reads the whole conversation from stdin.
        #
        # mcp_config_path is resolved to an absolute path *here*, against this
        # process's own cwd (the motor's, e.g. `backend/`) — never left relative.
        # The `claude` subprocess itself runs with cwd=workspace_path (the
        # target repo being investigated/implemented), so a relative path would
        # otherwise be resolved against the *wrong* directory: the MCP config is
        # a motor artifact (`config/*.json`), not something that lives inside
        # the target repo. Found for real running the `investigar` mode (ADR-007)
        # against a target repo whose workspace_path never had a `config/` dir.
        resolved_mcp_config_path = str(Path(mcp_config_path).resolve())
        return [
            self._claude_bin,
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--mcp-config",
            resolved_mcp_config_path,
            "--strict-mcp-config",
            "--json-schema",
            json.dumps(schema),
            "--permission-mode",
            "bypassPermissions",
        ]

    def _build_interactive_mcp_config(
        self, mcp_config_path: str, workspace_path: Any, run_id: str, step_name: str
    ) -> str:
        """Merges the static, motor-supplied MCP config (e.g. docs-mcp-proxy —
        `mcp_config_path`, resolved against this process's own cwd exactly like
        `_build_cmd` does for the non-interactive modes) with a per-run `ask-user`
        server entry, and writes the result to a deterministic path alongside
        session_log_path/instructions_path. The merged file — not the static one
        — is what `_build_cmd` receives as `mcp_config_path` for this modo.

        `ask-user`'s `command` is `sys.executable` (this process's own
        interpreter, guaranteed to have the `mcp` package installed) invoking
        `mcp_servers/ask_user_server.py` by absolute path — same "never leave a
        motor-relative path to be resolved against workspace_path" rule as the
        static config above (the `claude` subprocess runs with
        cwd=workspace_path, not the motor's). WORKSPACE_PATH/RUN_ID/STEP_NAME are
        passed as env so that server process knows which step's
        pergunta/resposta files (http_api.py, ADR-005-style convention) belong to
        it, without any in-memory state shared with this plugin.
        """
        resolved_static_path = Path(mcp_config_path).resolve()
        merged: dict = {"mcpServers": {}}
        if resolved_static_path.exists():
            raw = resolved_static_path.read_text(encoding="utf-8")
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "claude_code_runner (coding_local_interativo): mcp_config_path "
                    f"{resolved_static_path} is not valid JSON: {exc}"
                ) from exc
            if not isinstance(loaded, dict):
                raise ValueError(
                    "claude_code_runner (coding_local_interativo): mcp_config_path "
                    f"{resolved_static_path} must be a JSON object with a top-level "
                    f"'mcpServers' key, got {type(loaded).__name__}"
                )
            merged = loaded
            merged.setdefault("mcpServers", {})

        ask_user_server_path = (
            Path(__file__).resolve().parent.parent / "mcp_servers" / "ask_user_server.py"
        )
        merged["mcpServers"]["ask-user"] = {
            "command": sys.executable,
            "args": [str(ask_user_server_path)],
            "env": {
                "WORKSPACE_PATH": str(workspace_path),
                "RUN_ID": run_id,
                "STEP_NAME": step_name,
            },
        }

        merged_path = self._session_log_path(workspace_path, run_id, step_name).with_name(
            f"{step_name}.mcp-config.json"
        )
        merged_path.parent.mkdir(parents=True, exist_ok=True)
        merged_path.write_text(json.dumps(merged), encoding="utf-8")
        return str(merged_path)

    def _session_log_path(self, workspace_path: Any, run_id: str, step_name: str) -> Path:
        return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.log"

    def _instructions_path(self, workspace_path: Any, run_id: str, step_name: str) -> Path:
        return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.instrucoes.jsonl"

    def _pergunta_path(self, workspace_path: Any, run_id: str, step_name: str) -> Path:
        # Same file mcp_servers/ask_user_server.py writes while an `ask_user`
        # tool call is pending (and http_api.py reads for `awaiting_input`,
        # ADR-013) — duplicated here, not imported, same rule as every other
        # deterministic path already duplicated between this plugin and
        # adapters/http_api.py.
        return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.pergunta.json"

    def _run_streaming_session(
        self,
        cmd: list[str],
        cwd: Any,
        log_path: Path,
        instructions_path: Path,
        prompt: str,
        pergunta_path: Path | None = None,
    ) -> tuple[int, list[str]]:
        """Runs the CLI as a long-lived process, writing session_log_path
        incrementally (AC-02) and forwarding new instructions-file lines to its
        stdin while active (AC-04). Closes stdin as soon as the current turn's
        `result` event arrives — a stream-json session otherwise waits
        indefinitely for more input (verified live).

        `pergunta_path`, when given (only `coding_local_interativo`, ADR-013),
        marks a window where an `ask_user` MCP tool call is genuinely blocking
        the agent — `_poll_instructions` holds any new instruction unconsumed
        during that window rather than writing to stdin, since injecting a user
        message while a tool_use has no tool_result yet is unverified CLI
        behavior (unlike steering an ordinary turn, ADR-005, which *was*
        verified live).
        """
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # encoding="utf-8" is required, not cosmetic: `claude` always emits/reads
        # UTF-8 on stdout/stdin, but `text=True` alone falls back to
        # locale.getpreferredencoding() — a single-byte Windows codepage in this
        # environment, which raises UnicodeDecodeError on real (non-ASCII) output
        # and would silently mangle the Portuguese-accented prompts sent via
        # stdin otherwise. Found running the `investigar` modo for real (ADR-007).
        proc = self._popen_factory(
            cmd,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        stop_polling = threading.Event()
        poller = threading.Thread(
            target=self._poll_instructions,
            args=(proc, instructions_path, stop_polling, pergunta_path),
            daemon=True,
        )
        poller.start()

        lines: list[str] = []
        try:
            self._send_message(proc, prompt)
            with open(log_path, "w", encoding="utf-8") as log_file:
                for line in proc.stdout:
                    log_file.write(line)
                    log_file.flush()
                    lines.append(line)
                    if self._is_result_event(line):
                        stop_polling.set()
                        self._close_stdin(proc)
        finally:
            stop_polling.set()
            try:
                returncode = proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                proc.kill()
                returncode = proc.wait()
        return returncode, lines

    def _send_message(self, proc: Any, content: str) -> None:
        proc.stdin.write(
            json.dumps({"type": "user", "message": {"role": "user", "content": content}}) + "\n"
        )
        proc.stdin.flush()

    def _close_stdin(self, proc: Any) -> None:
        try:
            proc.stdin.close()
        except (OSError, ValueError):
            pass

    def _is_result_event(self, line: str) -> bool:
        try:
            return json.loads(line).get("type") == "result"
        except (json.JSONDecodeError, AttributeError):
            return False

    def _poll_instructions(
        self,
        proc: Any,
        instructions_path: Path,
        stop_event: threading.Event,
        pergunta_path: Path | None = None,
    ) -> None:
        last_size = 0
        while not stop_event.is_set():
            if stop_event.wait(self._instruction_poll_interval):
                return
            if pergunta_path is not None and pergunta_path.exists():
                # An `ask_user` call is blocking the agent right now (ADR-013) —
                # hold any new instruction unconsumed (don't advance last_size)
                # instead of writing to stdin mid-pending-tool-call; picked up on
                # a later poll once the question resolves and the file is gone.
                continue
            if not instructions_path.exists():
                continue
            try:
                data = instructions_path.read_text(encoding="utf-8")
            except OSError:
                continue
            if len(data) <= last_size:
                continue
            new_content = data[last_size:]
            last_size = len(data)
            for instruction_line in new_content.splitlines():
                instruction_line = instruction_line.strip()
                if not instruction_line:
                    continue
                try:
                    self._send_message(proc, instruction_line)
                except (BrokenPipeError, OSError, ValueError):
                    return  # process already closed stdin / exited

    def _find_result_event(self, lines: list[str]) -> dict | None:
        for line in reversed(lines):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("type") == "result":
                return payload
        return None

    def _extract_structured(self, result_event: dict | None, log_path: Path) -> dict:
        if result_event is None:
            raise RuntimeError(f"claude CLI produced no result event: see {log_path}")
        structured = result_event.get("structured_output")
        if isinstance(structured, dict):
            return structured
        result_field = result_event.get("result")
        if isinstance(result_field, str):
            try:
                parsed = json.loads(result_field)
            except json.JSONDecodeError:
                return {"summary": result_field}
            if isinstance(parsed, dict):
                return parsed
        raise RuntimeError(
            f"claude CLI result event has no usable structured output: see {log_path}"
        )

    def _raise_if_failed(self, returncode: int, lines: list[str], log_path: Path) -> None:
        if returncode != 0:
            joined = "".join(lines).lower()
            if any(pattern in joined for pattern in _TRANSIENT_PATTERNS):
                raise TransientError(
                    f"claude CLI failed transiently (exit {returncode}): see {log_path}"
                )
            raise RuntimeError(f"claude CLI failed (exit {returncode}): see {log_path}")
        result_event = self._find_result_event(lines)
        if result_event is not None and result_event.get("is_error"):
            raise RuntimeError(f"claude CLI reported an error result: see {log_path}")


PLUGIN = ClaudeCodeRunnerPlugin
