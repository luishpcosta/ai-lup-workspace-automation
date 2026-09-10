"""`ask_user` MCP server — the pause/resume mechanism for the `coding_local_interativo`
modo of the Claude Code Runner plugin (`plugins/claude_code_runner.py`).

Why a dedicated MCP tool, not the existing `instructions_path` channel (ADR-005):
`claude` in `--print` mode does not pause on its own — nothing stops the agent from
"asking a question" as plain text and immediately guessing an answer to finish its
turn (`--json-schema` forces a schema-conforming result at the end of every turn
regardless). A tool call is the one thing the CLI's own agentic loop genuinely
blocks on: the agent cannot proceed past a `tool_use` until it receives the matching
`tool_result`. `ask_user`, below, is that tool — calling it blocks the live `claude`
process for real, driven by the protocol itself, not by prompt convention.

Runs as a stdio MCP server (`FastMCP`), started as a subprocess of `claude` itself
(declared in the per-run merged `--mcp-config` that
`claude_code_runner.py::_build_interactive_mcp_config` writes). One process per
running step — `WORKSPACE_PATH`/`RUN_ID`/`STEP_NAME` are injected as env vars by
that merged config (same idea as `mcp-docs-proxy.json`'s `BASE_URL`), so this
process always knows exactly which step it belongs to.

File paths are deterministic, same directory/convention as `session_log_path`/
`instructions_path` (ADR-002/ADR-005) — one sibling pair per step:
    <workspace_path>/.workflow-logs/<run_id>/<step_name>.pergunta.json   (written here)
    <workspace_path>/.workflow-logs/<run_id>/<step_name>.resposta.json  (written by
        `POST /runs/{chain_name}/resposta`, http_api.py — polled here)

At most one question is pending per step at a time (the tool call itself blocks the
agent, so it cannot ask a second question before the first is answered) — no
question id is needed to correlate an answer to a question.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

#: How long to wait for a human answer before giving the agent a fallback
#: response and letting it proceed on its own judgement — an assumption, not a
#: validated number (same "adjustable starting point" spirit as ADR-008's
#: confirm_pr retry backoff), overridable per run via ASK_USER_TIMEOUT_SECONDS.
_DEFAULT_TIMEOUT_SECONDS = 1200.0

#: How often to check for the answer file — same order of magnitude as
#: claude_code_runner.py's own _poll_instructions default.
_POLL_INTERVAL_SECONDS = 0.5

mcp = FastMCP("ask-user")


def _workspace_path() -> Path:
    return Path(os.environ["WORKSPACE_PATH"])


def _run_id() -> str:
    return os.environ["RUN_ID"]


def _step_name() -> str:
    return os.environ["STEP_NAME"]


def _timeout_seconds() -> float:
    raw = os.environ.get("ASK_USER_TIMEOUT_SECONDS")
    if not raw:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        return float(raw)
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS


def _pergunta_path() -> Path:
    return _workspace_path() / ".workflow-logs" / _run_id() / f"{_step_name()}.pergunta.json"


def _resposta_path() -> Path:
    return _workspace_path() / ".workflow-logs" / _run_id() / f"{_step_name()}.resposta.json"


@mcp.tool()
def ask_user(question: str, options: list[str] | None = None) -> str:
    """Ask the human operator a question through the workflow panel and block until
    they answer (or the timeout elapses). Use this whenever you need a decision or
    clarification you cannot safely infer on your own — an ambiguous instruction, a
    choice between implementation approaches, confirmation before something hard to
    reverse. `options`, when given, are shown to the human as a fixed set of choices
    instead of a free-text field.
    """
    pergunta_path = _pergunta_path()
    resposta_path = _resposta_path()
    pergunta_path.parent.mkdir(parents=True, exist_ok=True)

    # Clear any stale answer left over from a previous question on this step
    # before publishing the new one — otherwise a leftover file could be
    # misread as the answer to *this* question the instant it's written.
    resposta_path.unlink(missing_ok=True)
    pergunta_path.write_text(
        json.dumps({"question": question, "options": options or [], "asked_at": time.time()}),
        encoding="utf-8",
    )

    deadline = time.monotonic() + _timeout_seconds()
    try:
        while time.monotonic() < deadline:
            if resposta_path.exists():
                try:
                    answer = resposta_path.read_text(encoding="utf-8").strip()
                finally:
                    resposta_path.unlink(missing_ok=True)
                if answer:
                    return answer
            time.sleep(_POLL_INTERVAL_SECONDS)
    finally:
        pergunta_path.unlink(missing_ok=True)

    return (
        "(sem resposta do usuário dentro do tempo limite — prossiga com seu melhor "
        "julgamento e registre no resumo final que esta pergunta ficou sem resposta)"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
