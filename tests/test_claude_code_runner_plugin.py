import json

import claude_code_runner
import pytest

from workflow_engine.domain.exceptions import TransientError
from workflow_engine.plugin_sdk import PluginContext


class FakeCliResult:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    def __init__(self, result: FakeCliResult):
        self.result = result
        self.calls: list = []

    def __call__(self, cmd, cwd=None, capture_output=False, text=False):
        self.calls.append(cmd)
        return self.result


def envelope(inner: dict) -> str:
    return json.dumps({"result": json.dumps(inner), "is_error": False})


def test_coding_mode_invokes_cli_and_returns_structured_result_ac04_ac05(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    cli_stdout = envelope({"summary": "implementado", "docs_referenced": ["ADR-002", "AC-14"]})
    runner = FakeRunner(FakeCliResult(0, stdout=cli_stdout))
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(run_command=runner)

    context = PluginContext(
        input={"workspace_path": str(workdir), "branch": "feature/HIST-1"},
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        run_id="run-1",
        step_name="implementar_historia",
    )

    output = plugin.run(context)

    assert output["status"] == "success"
    assert output["summary"] == "implementado"
    assert output["docs_referenced"] == ["ADR-002", "AC-14"]
    # carry-forward: workspace_path/branch from context.input survive into output
    assert output["branch"] == "feature/HIST-1"
    assert output["workspace_path"] == str(workdir)
    # session_log_path is deterministic and the file actually exists on disk
    expected_log = workdir / ".workflow-logs" / "run-1" / "implementar_historia.log"
    assert output["session_log_path"] == str(expected_log)
    assert expected_log.exists()
    # MCP flags verified against the installed CLI are present
    assert "--strict-mcp-config" in runner.calls[0]
    assert "--mcp-config" in runner.calls[0]


def test_review_mode_starts_fresh_session_ac06_ac07(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    cli_stdout = envelope({"summary": "revisão ok"})
    runner = FakeRunner(FakeCliResult(0, stdout=cli_stdout))
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(run_command=runner)

    context = PluginContext(
        input={"workspace_path": str(workdir), "pr_number": 42, "pr_url": "https://pr/42"},
        params={
            "modo": "review",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "skill": "code-review",
        },
        run_id="run-1",
        step_name="revisar_pr",
    )

    output = plugin.run(context)

    assert output["summary"] == "revisão ok"
    assert output["status"] == "success"
    expected_log = workdir / ".workflow-logs" / "run-1" / "revisar_pr.log"
    assert output["session_log_path"] == str(expected_log)
    assert expected_log.exists()
    cmd = runner.calls[0]
    assert "-r" not in cmd
    assert "--resume" not in cmd
    assert "-c" not in cmd
    assert "--continue" not in cmd
    assert "--fork-session" not in cmd


def test_failure_still_leaves_transcript_on_disk_ac08(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    runner = FakeRunner(FakeCliResult(1, stdout="", stderr="permission denied"))
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(run_command=runner)

    context = PluginContext(
        input={"workspace_path": str(workdir)},
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        run_id="run-1",
        step_name="implementar_historia",
    )

    with pytest.raises(RuntimeError):
        plugin.run(context)

    expected_log = workdir / ".workflow-logs" / "run-1" / "implementar_historia.log"
    assert expected_log.exists()
    assert "permission denied" in expected_log.read_text(encoding="utf-8")


def test_transient_stderr_pattern_is_retriable(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    runner = FakeRunner(FakeCliResult(1, stdout="", stderr="upstream rate_limit exceeded"))
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(run_command=runner)

    context = PluginContext(
        input={"workspace_path": str(workdir)},
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        run_id="run-1",
        step_name="implementar_historia",
    )

    with pytest.raises(TransientError):
        plugin.run(context)
