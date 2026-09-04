import git_pr
import pytest

from workflow_engine.domain.exceptions import TransientError
from workflow_engine.plugin_sdk import PluginContext


class FakeResult:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    def __init__(self, result: FakeResult):
        self.result = result
        self.calls: list = []

    def __call__(self, cmd, cwd=None, capture_output=False, text=False):
        self.calls.append(cmd)
        return self.result


def make_context(params, input_data):
    return PluginContext(input=input_data, params=params, run_id="run-1", step_name="abrir_pr")


def test_creates_pr_with_traceable_body_ac12_ac13():
    runner = FakeRunner(FakeResult(0, stdout="https://github.com/org/app/pull/42\n"))
    plugin = git_pr.GitPrPlugin(run_command=runner)

    context = make_context(
        params={
            "action": "create_pr",
            "branch": "feature/HIST-1",
            "base_branch": "main",
            "historia_id": "HIST-1",
            "title_template": "[HIST-1] {{ summary }}",
            "body_template": "Implementa HIST-1.\n\nDocs: {{ docs_referenced }}",
            "labels": ["automated-pr"],
        },
        input_data={
            "workspace_path": "/tmp/ws",
            "summary": "corrige bug X",
            "docs_referenced": ["ADR-002"],
        },
    )

    output = plugin.run(context)

    assert output["pr_number"] == 42
    assert output["pr_url"] == "https://github.com/org/app/pull/42"
    assert output["status"] == "created"
    # carry-forward: everything from context.input survives into output
    assert output["summary"] == "corrige bug X"
    assert output["docs_referenced"] == ["ADR-002"]

    cmd = runner.calls[0]
    assert "gh" in cmd and "create" in cmd
    assert "--label" in cmd
    title_idx = cmd.index("--title") + 1
    assert cmd[title_idx] == "[HIST-1] corrige bug X"


def test_missing_traceability_blocks_pr_creation_ac14():
    runner = FakeRunner(FakeResult(0, stdout="https://github.com/org/app/pull/1\n"))
    plugin = git_pr.GitPrPlugin(run_command=runner)

    context = make_context(
        params={
            "action": "create_pr",
            "branch": "feature/x",
            "base_branch": "main",
            "historia_id": "HIST-1",
            "title_template": "fix",
            "body_template": "Just a fix, no references here.",
        },
        input_data={"docs_referenced": ["ADR-002"]},
    )

    with pytest.raises(ValueError, match="historia_id"):
        plugin.run(context)

    assert runner.calls == []  # gh was never invoked


def test_missing_docs_reference_blocks_pr_creation_ac14():
    runner = FakeRunner(FakeResult(0, stdout="https://github.com/org/app/pull/1\n"))
    plugin = git_pr.GitPrPlugin(run_command=runner)

    context = make_context(
        params={
            "action": "create_pr",
            "branch": "feature/x",
            "base_branch": "main",
            "historia_id": "HIST-1",
            "title_template": "fix",
            "body_template": "Implementa HIST-1, mas sem citar os docs.",
        },
        input_data={"docs_referenced": ["ADR-002"]},
    )

    with pytest.raises(ValueError, match="docs_referenced"):
        plugin.run(context)

    assert runner.calls == []


def test_update_pr_edits_existing_without_duplicating_ac15():
    runner = FakeRunner(FakeResult(0, stdout=""))
    plugin = git_pr.GitPrPlugin(run_command=runner)

    context = make_context(
        params={
            "action": "update_pr",
            "branch": "feature/HIST-1",
            "base_branch": "main",
            "historia_id": "HIST-1",
            "pr_number": 42,
            "pr_url": "https://github.com/org/app/pull/42",
            "title_template": "[HIST-1] update",
            "body_template": "Implementa HIST-1. Docs: {{ docs_referenced }}",
        },
        input_data={"docs_referenced": ["ADR-002"]},
    )

    output = plugin.run(context)

    assert output["status"] == "updated"
    assert output["pr_number"] == 42
    cmd = runner.calls[0]
    assert cmd[:3] == ["gh", "pr", "edit"]
    assert "42" in cmd
    assert "--add-label" not in cmd  # no labels configured in this test


def test_title_over_256_chars_is_truncated():
    runner = FakeRunner(FakeResult(0, stdout="https://github.com/org/app/pull/7\n"))
    plugin = git_pr.GitPrPlugin(run_command=runner)

    long_summary = "x" * 1007
    context = make_context(
        params={
            "action": "create_pr",
            "branch": "feature/x",
            "base_branch": "main",
            "historia_id": "HIST-1",
            "title_template": "[HIST-1] {{ summary }}",
            "body_template": "Implementa HIST-1.",
        },
        input_data={"summary": long_summary},
    )

    plugin.run(context)

    cmd = runner.calls[0]
    title = cmd[cmd.index("--title") + 1]
    assert len(title) == 256
    assert title.endswith("…")


def test_gh_transient_failure_is_retriable():
    runner = FakeRunner(FakeResult(1, stdout="", stderr="Could not resolve host: github.com"))
    plugin = git_pr.GitPrPlugin(run_command=runner)

    context = make_context(
        params={
            "action": "create_pr",
            "branch": "feature/x",
            "base_branch": "main",
            "historia_id": "HIST-1",
            "title_template": "t",
            "body_template": "Implementa HIST-1.",
        },
        input_data={},
    )

    with pytest.raises(TransientError):
        plugin.run(context)
