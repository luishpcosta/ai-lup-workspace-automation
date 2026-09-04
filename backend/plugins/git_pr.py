"""Git/PR plugin (ADR-002, AT-05; AC-12..AC-15).

Creates/updates a Pull Request via the `gh` CLI. Flags verified against the
installed CLI (`gh 2.97.0`, `gh pr create --help` / `gh pr edit --help`):
`create` takes `--label` (repeatable), `edit` takes `--add-label` instead —
these are NOT interchangeable, unlike what a naive guess might assume. The
body always goes through `--body-file` (a temp file), never `--body` inline,
to avoid shell-escaping issues with content coming from rendered templates.

Traceability validation (AC-14) runs *before* any `gh` call on `create_pr`:
the rendered body must reference `historia_id` and, when `docs_referenced` is
non-empty, at least one of those ids — otherwise this raises a permanent
(non-retriable) failure and no PR is opened.

`{{ field }}` inside `title_template`/`body_template` is resolved here, at
runtime, from `context.input` merged with `params` (input wins on collision)
— a different mechanism, with different timing, than the Chain Loader's
`{{ vars.<key> }}` (ADR-002, RF-5): by the time a template reaches this
plugin, `{{ vars.* }}` refs are already substituted; only refs to chain data
(`summary`, `docs_referenced`, ...) remain. A list value is auto-joined with
", " — no filter syntax (`| join(...)`) is supported, to avoid pulling in a
templating dependency for this POC.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Any

from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError

_TEMPLATE_REF = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_PR_NUMBER_FROM_URL = re.compile(r"/pull/(\d+)")
_TRANSIENT_STDERR_PATTERNS = ("timeout", "econnreset", "network", "could not resolve host")


class GitPrPlugin(Plugin):
    def __init__(self, run_command=subprocess.run):
        self._run_command = run_command

    def run(self, context: PluginContext) -> Any:
        params = context.params
        input_data = context.input if isinstance(context.input, dict) else {}
        action = params["action"]
        cwd = input_data.get("workspace_path")

        render_data = {**params, **input_data}
        title = self._truncate_title(self._render(params["title_template"], render_data))
        body = self._render(params["body_template"], render_data)

        if action == "create_pr":
            self._validate_traceability(body, params, input_data)
            result = self._create_pr(params, title, body, cwd)
        elif action == "update_pr":
            result = self._update_pr(params, title, body, cwd)
        else:
            raise ValueError(f"git_pr: invalid action {action!r}")

        return {**input_data, **result}

    def _render(self, template: str, data: dict) -> str:
        def _sub(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in data:
                return match.group(0)
            value = data[key]
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return str(value)

        return _TEMPLATE_REF.sub(_sub, template)

    def _truncate_title(self, title: str) -> str:
        """GitHub rejects PR titles over 256 chars (verified live — a real run hit
        `GraphQL: Title is too long (maximum is 256 characters)` when title_template
        embedded an agent-generated `summary` that happened to be over 1000 chars).
        A template can't know in advance how long an interpolated field will be, so
        this is a defensive backstop, not something a template author should have to
        get right themselves.
        """
        max_length = 256
        if len(title) <= max_length:
            return title
        return title[: max_length - 1].rstrip() + "…"

    def _validate_traceability(self, body: str, params: dict, input_data: dict) -> None:
        historia_id = params.get("historia_id", "")
        if not historia_id or historia_id not in body:
            raise ValueError(
                "git_pr: body_template must reference historia_id — refusing to open "
                "a PR without traceability to its source story"
            )
        docs_referenced = input_data.get("docs_referenced") or []
        if docs_referenced and not any(doc_id in body for doc_id in docs_referenced):
            raise ValueError(
                "git_pr: body_template must reference at least one of docs_referenced "
                "— refusing to open a PR without traceability to the docs consulted"
            )

    def _create_pr(self, params: dict, title: str, body: str, cwd: str | None) -> dict:
        with self._body_file(body) as body_file:
            cmd = [
                "gh",
                "pr",
                "create",
                "--base",
                params["base_branch"],
                "--head",
                params["branch"],
                "--title",
                title,
                "--body-file",
                body_file,
            ]
            for label in params.get("labels") or []:
                cmd += ["--label", label]
            result = self._run_command(cmd, cwd=cwd, capture_output=True, text=True)

        self._raise_if_failed(result)
        pr_url = (result.stdout or "").strip().splitlines()[-1] if result.stdout else ""
        return {
            "pr_number": self._pr_number_from_url(pr_url),
            "pr_url": pr_url,
            "status": "created",
        }

    def _update_pr(self, params: dict, title: str, body: str, cwd: str | None) -> dict:
        pr_number = params.get("pr_number")
        if not pr_number:
            raise ValueError("git_pr: 'pr_number' is required when action is 'update_pr'")

        with self._body_file(body) as body_file:
            cmd = ["gh", "pr", "edit", str(pr_number), "--title", title, "--body-file", body_file]
            for label in params.get("labels") or []:
                cmd += ["--add-label", label]
            result = self._run_command(cmd, cwd=cwd, capture_output=True, text=True)

        self._raise_if_failed(result)
        pr_url = params.get("pr_url", "")
        return {"pr_number": pr_number, "pr_url": pr_url, "status": "updated"}

    def _body_file(self, body: str):
        class _TempBodyFile:
            def __enter__(_self):
                fd, path = tempfile.mkstemp(suffix=".md", text=True)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(body)
                _self.path = path
                return path

            def __exit__(_self, *exc_info):
                os.unlink(_self.path)

        return _TempBodyFile()

    def _pr_number_from_url(self, pr_url: str) -> int | None:
        match = _PR_NUMBER_FROM_URL.search(pr_url)
        return int(match.group(1)) if match else None

    def _raise_if_failed(self, result) -> None:
        if result.returncode == 0:
            return
        lowered = (result.stderr or "").lower()
        if any(pattern in lowered for pattern in _TRANSIENT_STDERR_PATTERNS):
            raise TransientError(f"gh CLI failed transiently (exit {result.returncode})")
        raise RuntimeError(f"gh CLI failed (exit {result.returncode}): {result.stderr}")


PLUGIN = GitPrPlugin
