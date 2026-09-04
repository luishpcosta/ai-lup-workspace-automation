"""Shell/Script Runner plugin (ADR-002, AT-04; AC-09..AC-11).

Runs a local `.sh`/`.bat` script via subprocess (e.g. polling a PR's CI
checks). Since a script is an external process with no access to the Python
`context`, every field of `context.input` is exposed to it as an environment
variable `WORKFLOW_INPUT_<KEY_UPPERCASE>` (e.g. `pr_number` ->
`WORKFLOW_INPUT_PR_NUMBER`) — this is how a polling script started right
after Git/PR knows which PR to check.

Also carries `context.input` forward into its own `output` (merged, own keys
win) — the review step, two hops after Git/PR, needs `pr_number`/`pr_url` and
this is the only hop between them.

Runs with `cwd = context.input["workspace_path"]` when present (falls back to
the automation process's own cwd otherwise) — a relative `script_path` like
`./scripts/poll_ci_checks.sh` is meant to resolve inside the cloned repo, not
wherever `workflow run` itself was launched from. Found while wiring up a real
end-to-end run against `samples/target-cli`.

A non-zero `exit_code` is returned as data, not raised as a failure — the
caller decides what a given script's exit code means. Only a timeout is
treated as retriable (AC-11); nothing here inspects `exit_code` itself.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError


class ShellScriptRunnerPlugin(Plugin):
    def __init__(self, run_command=subprocess.run):
        self._run_command = run_command

    def run(self, context: PluginContext) -> Any:
        params = context.params
        input_data = context.input if isinstance(context.input, dict) else {}
        script_path = params["script_path"]
        interpreter = params["interpreter"]
        args = params.get("args") or []
        timeout_seconds = params.get("timeout_seconds")

        cmd = self._build_command(interpreter, script_path, args)
        env = self._build_env(input_data)
        cwd = input_data.get("workspace_path")

        try:
            result = self._run_command(
                cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout_seconds
            )
        except subprocess.TimeoutExpired as exc:
            raise TransientError(
                f"script timed out after {timeout_seconds}s: {script_path}"
            ) from exc

        return {
            **input_data,
            "exit_code": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
        }

    def _build_command(self, interpreter: str, script_path: str, args: list) -> list[str]:
        if interpreter == "bash":
            return ["bash", script_path, *args]
        if interpreter == "bat":
            return ["cmd", "/c", script_path, *args]
        raise ValueError(f"shell_script_runner: invalid interpreter {interpreter!r}")

    def _build_env(self, input_data: dict) -> dict:
        env = dict(os.environ)
        for key, value in input_data.items():
            env_key = f"WORKFLOW_INPUT_{key.upper()}"
            env[env_key] = (
                ",".join(str(v) for v in value) if isinstance(value, list) else str(value)
            )
        return env


PLUGIN = ShellScriptRunnerPlugin
