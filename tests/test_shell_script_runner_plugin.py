import subprocess

import pytest
import shell_script_runner

from workflow_engine.domain.exceptions import TransientError
from workflow_engine.plugin_sdk import PluginContext


class FakeRunner:
    def __init__(self, result=None, raise_timeout=False, timeout_seconds=None):
        self.result = result
        self.raise_timeout = raise_timeout
        self.timeout_seconds = timeout_seconds
        self.calls: list = []
        self.last_env: dict | None = None
        self.last_cwd = None

    def __call__(self, cmd, cwd=None, env=None, capture_output=False, text=False, timeout=None):
        self.calls.append(cmd)
        self.last_env = env
        self.last_cwd = cwd
        if self.raise_timeout:
            raise subprocess.TimeoutExpired(cmd, timeout)
        return self.result


def make_context(params, input_data):
    return PluginContext(
        input=input_data, params=params, run_id="run-1", step_name="aguardar_checks"
    )


def test_runs_script_and_returns_exit_code_stdout_stderr_ac09():
    runner = FakeRunner(result=subprocess.CompletedProcess([], 0, stdout="ok\n", stderr=""))
    plugin = shell_script_runner.ShellScriptRunnerPlugin(run_command=runner)

    output = plugin.run(
        make_context(
            {"script_path": "./scripts/poll_ci_checks.sh", "interpreter": "bash"},
            input_data={},
        )
    )

    assert output["exit_code"] == 0
    assert output["stdout"] == "ok\n"
    assert output["stderr"] == ""
    assert runner.calls[0] == ["bash", "./scripts/poll_ci_checks.sh"]


def test_carries_forward_input_and_exposes_it_as_env_vars_ac10():
    runner = FakeRunner(result=subprocess.CompletedProcess([], 0, stdout="", stderr=""))
    plugin = shell_script_runner.ShellScriptRunnerPlugin(run_command=runner)

    output = plugin.run(
        make_context(
            {"script_path": "./poll.sh", "interpreter": "bash"},
            input_data={"pr_number": 42, "pr_url": "https://pr/42", "docs_referenced": ["ADR-002"]},
        )
    )

    # carry-forward into output
    assert output["pr_number"] == 42
    assert output["pr_url"] == "https://pr/42"
    assert output["docs_referenced"] == ["ADR-002"]
    # exposed to the script as env vars
    assert runner.last_env["WORKFLOW_INPUT_PR_NUMBER"] == "42"
    assert runner.last_env["WORKFLOW_INPUT_PR_URL"] == "https://pr/42"
    assert runner.last_env["WORKFLOW_INPUT_DOCS_REFERENCED"] == "ADR-002"


def test_runs_inside_workspace_path_from_input(tmp_path):
    runner = FakeRunner(result=subprocess.CompletedProcess([], 0, stdout="", stderr=""))
    plugin = shell_script_runner.ShellScriptRunnerPlugin(run_command=runner)

    plugin.run(
        make_context(
            {"script_path": "./scripts/poll.sh", "interpreter": "bash"},
            input_data={"workspace_path": str(tmp_path)},
        )
    )

    assert runner.last_cwd == str(tmp_path)


def test_timeout_is_retriable_ac11():
    runner = FakeRunner(raise_timeout=True)
    plugin = shell_script_runner.ShellScriptRunnerPlugin(run_command=runner)

    with pytest.raises(TransientError):
        plugin.run(
            make_context(
                {"script_path": "./poll.sh", "interpreter": "bash", "timeout_seconds": 600},
                input_data={},
            )
        )


def test_bat_interpreter_uses_cmd():
    runner = FakeRunner(result=subprocess.CompletedProcess([], 0, stdout="", stderr=""))
    plugin = shell_script_runner.ShellScriptRunnerPlugin(run_command=runner)

    plugin.run(
        make_context(
            {"script_path": "./poll.bat", "interpreter": "bat", "args": ["--flag"]},
            input_data={},
        )
    )

    assert runner.calls[0] == ["cmd", "/c", "./poll.bat", "--flag"]
