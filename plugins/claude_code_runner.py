"""Claude Code Runner plugin (ADR-002, AT-02/AT-03; AC-04..AC-08).

Invokes the `claude` CLI headless (`-p`/`--print`), parametrized by
`params.modo` (`"coding"` or `"review"`). Invocation verified against the
installed CLI (`claude 2.1.260`, `claude --help`) — see
`adr/ADR-002-plugins-poc-pipeline-sdd.md`, "Invocação verificada da CLI":

- `--mcp-config <path> --strict-mcp-config`: always points explicitly at the
  Docusaurus MCP config; never relies on project auto-discovered `.mcp.json`
  (which stays "Pending approval" — unusable headless).
- `--output-format json --json-schema <schema>`: structured result, so
  `summary`/`docs_referenced` don't need free-text parsing. Verified live
  (real `claude -p` call against the sample MCP server, see
  `progress.md`): the outer envelope's `result` field is a **JSON-encoded
  string** matching the schema (`{"result": "{\"summary\": ...}", ...}`),
  not a nested object — `_parse_result` below relies on exactly this shape.
- `--permission-mode bypassPermissions`: **not** `acceptEdits` +
  `--permission-prompts none` — that combination was tried first and
  verified *not* to work: it denies MCP tool calls outright
  (`permission_denials` in the CLI's own JSON output), since `acceptEdits`
  only pre-approves file edits, not arbitrary tool use, and
  `--permission-prompts none` denies anything needing a decision instead of
  approving it. `bypassPermissions` is the mode verified to actually let a
  headless run call MCP tools.
- Review mode never passes `-r/--resume`, `-c/--continue` or `--fork-session`
  — that absence is what guarantees a fresh session/context window.

`session_log_path` is deterministic (`<workspace_path>/.workflow-logs/<run_id>/
<step_name>.log`), not something only returned in `output` — the file is
written in a `finally` block, so it exists even when the plugin raises
(AC-08), which a normal `output` return can't guarantee (ADR-001: failure =
exception, no structured output).

Both modes carry `context.input` forward into their own `output` (merged,
own keys win) — `workspace_path` has no other param through which to reach
the review step two hops later (via Git/PR, then Shell/Script Runner).
"""

from __future__ import annotations

import json
import subprocess
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

#: exit-code!=0 whose stderr matches one of these is treated as retriable;
#: anything else is a permanent failure.
_TRANSIENT_STDERR_PATTERNS = ("rate_limit", "econnreset", "timeout", "network", "overloaded")


class ClaudeCodeRunnerPlugin(Plugin):
    def __init__(self, run_command=subprocess.run, claude_bin: str = "claude"):
        self._run_command = run_command
        self._claude_bin = claude_bin

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
        cmd = [
            self._claude_bin,
            "-p",
            self._coding_prompt(historia_id),
            "--mcp-config",
            mcp_config_path,
            "--strict-mcp-config",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(_CODING_SCHEMA),
            "--permission-mode",
            "bypassPermissions",
        ]
        returncode, stdout, stderr = self._invoke_cli(cmd, workdir, log_path)
        self._raise_if_failed(returncode, stderr, log_path)
        result = self._parse_result(stdout, log_path)

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
        # Deliberately no -r/--resume, -c/--continue or --fork-session: this is
        # what makes the review run in a fresh session/context window, per the
        # scenario's requirement (no reuse of the coding session's history).
        cmd = [
            self._claude_bin,
            "-p",
            self._review_prompt(skill, pr_ref),
            "--mcp-config",
            mcp_config_path,
            "--strict-mcp-config",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(_REVIEW_SCHEMA),
            "--permission-mode",
            "bypassPermissions",
        ]
        returncode, stdout, stderr = self._invoke_cli(cmd, workdir, log_path)
        self._raise_if_failed(returncode, stderr, log_path)
        result = self._parse_result(stdout, log_path)

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

    def _session_log_path(self, workspace_path: Any, run_id: str, step_name: str) -> Path:
        return Path(workspace_path) / ".workflow-logs" / run_id / f"{step_name}.log"

    def _invoke_cli(self, cmd: list[str], cwd: Any, log_path: Path) -> tuple[int, str, str]:
        """Run the CLI, writing the transcript to log_path even on failure (AC-08)."""
        stdout, stderr, returncode = "", "", None
        try:
            result = self._run_command(cmd, cwd=str(cwd), capture_output=True, text=True)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            returncode = result.returncode
            return returncode, stdout, stderr
        finally:
            self._write_log(log_path, cmd, stdout, stderr)

    def _write_log(self, log_path: Path, cmd: list[str], stdout: str, stderr: str) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"$ {' '.join(cmd)}\n\n=== stdout ===\n{stdout}\n\n=== stderr ===\n{stderr}\n",
            encoding="utf-8",
        )

    def _raise_if_failed(self, returncode: int | None, stderr: str, log_path: Path) -> None:
        if returncode == 0:
            return
        lowered = stderr.lower()
        if any(pattern in lowered for pattern in _TRANSIENT_STDERR_PATTERNS):
            raise TransientError(
                f"claude CLI failed transiently (exit {returncode}): see {log_path}"
            )
        raise RuntimeError(f"claude CLI failed (exit {returncode}): see {log_path}")

    def _parse_result(self, stdout: str, log_path: Path) -> dict:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"claude CLI returned non-JSON output: see {log_path}") from exc

        result = payload
        if isinstance(payload, dict) and "result" in payload:
            inner = payload["result"]
            if isinstance(inner, str):
                try:
                    result = json.loads(inner)
                except json.JSONDecodeError:
                    result = {"summary": inner}
            elif isinstance(inner, dict):
                result = inner

        if not isinstance(result, dict):
            raise RuntimeError(f"claude CLI returned unexpected JSON shape: see {log_path}")
        return result


PLUGIN = ClaudeCodeRunnerPlugin
