"""Claude Code Runner plugin (ADR-002, AT-02/AT-03; ADR-005, AT-01..AT-03).

Invokes the `claude` CLI as a **long-lived process** (`Popen`, stdin/stdout kept
open) using `--input-format stream-json --output-format stream-json --verbose`,
parametrized by `params.modo` (`"coding"` or `"review"`). This replaced the
ADR-002 one-shot `subprocess.run(capture_output=True)` invocation — the plugin's
external contract (`params`/`output`, `TransientError` semantics) is unchanged.

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

    # -- shared plumbing -------------------------------------------------

    def _build_cmd(self, mcp_config_path: str, schema: dict) -> list[str]:
        # Deliberately no -r/--resume, -c/--continue or --fork-session: every
        # call is a fresh session/context window (verified live — see module
        # docstring). No positional prompt either: --input-format stream-json
        # reads the whole conversation from stdin.
        return [
            self._claude_bin,
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--mcp-config",
            mcp_config_path,
            "--strict-mcp-config",
            "--json-schema",
            json.dumps(schema),
            "--permission-mode",
            "bypassPermissions",
        ]

    def _session_log_path(self, workspace_path: Any, run_id: str, step_name: str) -> Path:
        return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.log"

    def _instructions_path(self, workspace_path: Any, run_id: str, step_name: str) -> Path:
        return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.instrucoes.jsonl"

    def _run_streaming_session(
        self, cmd: list[str], cwd: Any, log_path: Path, instructions_path: Path, prompt: str
    ) -> tuple[int, list[str]]:
        """Runs the CLI as a long-lived process, writing session_log_path
        incrementally (AC-02) and forwarding new instructions-file lines to its
        stdin while active (AC-04). Closes stdin as soon as the current turn's
        `result` event arrives — a stream-json session otherwise waits
        indefinitely for more input (verified live).
        """
        log_path.parent.mkdir(parents=True, exist_ok=True)
        proc = self._popen_factory(
            cmd,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        stop_polling = threading.Event()
        poller = threading.Thread(
            target=self._poll_instructions,
            args=(proc, instructions_path, stop_polling),
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
        self, proc: Any, instructions_path: Path, stop_event: threading.Event
    ) -> None:
        last_size = 0
        while not stop_event.is_set():
            if stop_event.wait(self._instruction_poll_interval):
                return
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
