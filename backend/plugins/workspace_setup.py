"""Workspace Setup plugin (ADR-002, AT-01; AC-01/AC-02/AC-03).

Prepares a local workspace before a coding step: clones/updates the target
repo, checks out the working branch from the base branch, optionally installs
dependencies and brings up local dockerized infrastructure.

`workspace_path` follows a deterministic convention (ADR-002, Decisão) so
retries are idempotent and downstream steps (Claude Code Runner's
`session_log_path`) can rely on it without a lookup:

    <workspaces_root>/<repo_slug>__<historia_id>

`workspaces_root` is plugin-level environment config (`WORKFLOW_WORKSPACES_ROOT`
env var, default `./workspaces`), never a step `param` — see ADR-002.

Error mapping (deliberate simplification, not tested by a formal AC beyond
AC-03): only the optional docker-compose step is wrapped as `TransientError`.
Git/install failures propagate as-is (permanent failure) — distinguishing a
transient network blip from a permanent config error (e.g. an unknown branch)
would need fragile stderr parsing that no acceptance criterion requires.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError


def _default_workspaces_root() -> Path:
    return Path(os.environ.get("WORKFLOW_WORKSPACES_ROOT", "./workspaces"))


class WorkspaceSetupPlugin(Plugin):
    def __init__(self, run_command=subprocess.run, workspaces_root: Path | None = None):
        self._run_command = run_command
        self._workspaces_root = Path(workspaces_root or _default_workspaces_root())

    def run(self, context: PluginContext) -> Any:
        params = context.params
        repo_url = params["repo_url"]
        branch_base = params["branch_base"]
        branch_name = params["branch_name"]
        historia_id = params["historia_id"]

        workspace_path = self._workspace_path(repo_url, historia_id)
        self._ensure_repo(workspace_path, repo_url)
        self._checkout(workspace_path, branch_base)
        base_commit_sha = self._rev_parse(workspace_path)
        self._checkout_new_branch(workspace_path, branch_name, branch_base)

        install_cmd = params.get("install_cmd")
        if install_cmd:
            self._git(install_cmd, cwd=workspace_path, shell=True)

        docker_compose_path = params.get("docker_compose_path")
        if docker_compose_path:
            self._up_docker_compose(docker_compose_path, cwd=workspace_path)

        return {
            "workspace_path": str(workspace_path),
            "branch": branch_name,
            "base_commit_sha": base_commit_sha,
            "status": "ready",
        }

    def _workspace_path(self, repo_url: str, historia_id: str) -> Path:
        repo_slug = repo_url.rstrip("/").rsplit("/", 1)[-1]
        if repo_slug.endswith(".git"):
            repo_slug = repo_slug[: -len(".git")]
        return self._workspaces_root / f"{repo_slug}__{historia_id}"

    def _ensure_repo(self, workspace_path: Path, repo_url: str) -> None:
        if (workspace_path / ".git").is_dir():
            self._git(["git", "fetch", "origin"], cwd=workspace_path)
            return
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        self._git(["git", "clone", repo_url, str(workspace_path)])

    def _checkout(self, workspace_path: Path, branch: str) -> None:
        self._git(["git", "checkout", branch], cwd=workspace_path)
        self._git(["git", "pull"], cwd=workspace_path)

    def _checkout_new_branch(
        self, workspace_path: Path, branch_name: str, branch_base: str
    ) -> None:
        self._git(["git", "checkout", "-B", branch_name, branch_base], cwd=workspace_path)

    def _rev_parse(self, workspace_path: Path) -> str:
        result = self._git(["git", "rev-parse", "HEAD"], cwd=workspace_path, capture_output=True)
        return (result.stdout or "").strip()

    def _git(self, cmd, cwd: Path | None = None, shell: bool = False, capture_output: bool = False):
        return self._run_command(
            cmd,
            cwd=str(cwd) if cwd else None,
            shell=shell,
            capture_output=capture_output,
            text=True,
            check=True,
        )

    def _up_docker_compose(self, docker_compose_path: str, cwd: Path) -> None:
        try:
            self._run_command(
                ["docker", "compose", "-f", docker_compose_path, "up", "-d"],
                cwd=str(cwd),
                shell=False,
                capture_output=False,
                text=True,
                check=True,
            )
        except Exception as exc:  # noqa: BLE001 - any failure here is retriable (AC-03)
            raise TransientError(f"docker compose up failed: {exc}") from exc


PLUGIN = WorkspaceSetupPlugin
