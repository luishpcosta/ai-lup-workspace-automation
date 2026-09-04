import subprocess

import pytest
import workspace_setup

from workflow_engine.domain.exceptions import TransientError
from workflow_engine.plugin_sdk import PluginContext


class FakeRunner:
    """Stands in for subprocess.run — no real git/docker call happens in tests."""

    def __init__(self):
        self.calls: list = []
        self.fail_docker = False

    def __call__(self, cmd, cwd=None, shell=False, capture_output=False, text=False, check=False):
        self.calls.append(cmd)
        if self.fail_docker and isinstance(cmd, list) and cmd[:2] == ["docker", "compose"]:
            raise subprocess.CalledProcessError(1, cmd)
        if isinstance(cmd, list) and cmd[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def make_context(params: dict) -> PluginContext:
    return PluginContext(input=None, params=params, run_id="run-1", step_name="preparar_ambiente")


def test_prepares_workspace_and_returns_deterministic_path_ac01(tmp_path):
    runner = FakeRunner()
    plugin = workspace_setup.WorkspaceSetupPlugin(run_command=runner, workspaces_root=tmp_path)

    output = plugin.run(
        make_context(
            {
                "repo_url": "git@github.com:org/app-alvo.git",
                "branch_base": "main",
                "branch_name": "feature/HIST-142",
                "historia_id": "HIST-142",
                "install_cmd": "npm install",
            }
        )
    )

    assert output["workspace_path"] == str(tmp_path / "app-alvo__HIST-142")
    assert output["branch"] == "feature/HIST-142"
    assert output["status"] == "ready"
    assert "npm install" in runner.calls


def test_returns_base_commit_sha_from_branch_base_ac02(tmp_path):
    runner = FakeRunner()
    plugin = workspace_setup.WorkspaceSetupPlugin(run_command=runner, workspaces_root=tmp_path)

    output = plugin.run(
        make_context(
            {
                "repo_url": "https://example.com/org/app.git",
                "branch_base": "main",
                "branch_name": "feature/x",
                "historia_id": "HIST-1",
            }
        )
    )

    assert output["base_commit_sha"] == "abc123"


def test_docker_compose_failure_is_transient_ac03(tmp_path):
    runner = FakeRunner()
    runner.fail_docker = True
    plugin = workspace_setup.WorkspaceSetupPlugin(run_command=runner, workspaces_root=tmp_path)

    with pytest.raises(TransientError):
        plugin.run(
            make_context(
                {
                    "repo_url": "https://example.com/org/app.git",
                    "branch_base": "main",
                    "branch_name": "feature/x",
                    "historia_id": "HIST-1",
                    "docker_compose_path": "./docker/local-deps.compose.yaml",
                }
            )
        )


def test_docker_compose_skipped_when_not_configured(tmp_path):
    runner = FakeRunner()
    plugin = workspace_setup.WorkspaceSetupPlugin(run_command=runner, workspaces_root=tmp_path)

    plugin.run(
        make_context(
            {
                "repo_url": "https://example.com/org/app.git",
                "branch_base": "main",
                "branch_name": "feature/x",
                "historia_id": "HIST-1",
            }
        )
    )

    assert not any(isinstance(c, list) and c[:2] == ["docker", "compose"] for c in runner.calls)
