import json
import time
from pathlib import Path

import claude_code_runner
import pytest

from workflow_engine.domain.exceptions import TransientError
from workflow_engine.plugin_sdk import PluginContext


class FakeStdin:
    def __init__(self):
        self.lines: list[str] = []
        self.closed = False

    def write(self, data: str) -> None:
        if self.closed:
            raise ValueError("write to closed file")
        self.lines.append(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class DelayedLines:
    """Yields pre-set lines with a small real delay between them — gives the
    background instructions-poller thread real wall-clock time to act, mirroring
    how a live subprocess trickles out output instead of dumping it all at once.
    """

    def __init__(self, lines: list[str], delay: float = 0.03):
        self._lines = lines
        self._delay = delay

    def __iter__(self):
        for line in self._lines:
            time.sleep(self._delay)
            yield line


class FakePopen:
    def __init__(self, output_lines: list[str], returncode: int):
        self.stdin = FakeStdin()
        self.stdout = DelayedLines(output_lines)
        self.returncode = returncode
        self.killed = False

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.killed = True


class FakePopenFactory:
    def __init__(self, output_lines: list[str], returncode: int = 0):
        self.output_lines = output_lines
        self.returncode = returncode
        self.calls: list[list[str]] = []
        self.kwargs: list[dict] = []
        self.procs: list[FakePopen] = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        self.kwargs.append(kwargs)
        proc = FakePopen(self.output_lines, self.returncode)
        self.procs.append(proc)
        return proc


def result_line(inner: dict, is_error: bool = False) -> str:
    return (
        json.dumps(
            {
                "type": "result",
                "result": json.dumps(inner),
                "structured_output": inner,
                "is_error": is_error,
            }
        )
        + "\n"
    )


def system_line() -> str:
    return json.dumps({"type": "system", "subtype": "init"}) + "\n"


def make_context(params, input_data, run_id="run-1", step_name="s1"):
    return PluginContext(input=input_data, params=params, run_id=run_id, step_name=step_name)


def test_coding_mode_invokes_cli_and_returns_structured_result_ac04_ac05(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [
        system_line(),
        result_line({"summary": "implementado", "docs_referenced": ["ADR-002", "AC-14"]}),
    ]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir), "branch": "feature/HIST-1"},
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
    cmd = factory.calls[0]
    assert "--strict-mcp-config" in cmd
    assert "--mcp-config" in cmd
    assert "--input-format" in cmd
    assert "stream-json" in cmd
    # initial prompt is sent via stdin (stream-json input), not a positional arg
    sent = factory.procs[0].stdin.lines
    assert sent, "expected at least one message written to stdin"
    first_message = json.loads(sent[0])
    assert first_message["type"] == "user"
    assert "HIST-1" in first_message["message"]["content"]


def test_review_mode_starts_fresh_session_ac06_ac07(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [system_line(), result_line({"summary": "revisão ok"})]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "review",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "skill": "code-review",
        },
        input_data={"workspace_path": str(workdir), "pr_number": 42, "pr_url": "https://pr/42"},
        step_name="revisar_pr",
    )

    output = plugin.run(context)

    assert output["summary"] == "revisão ok"
    assert output["status"] == "success"
    expected_log = workdir / ".workflow-logs" / "run-1" / "revisar_pr.log"
    assert output["session_log_path"] == str(expected_log)
    assert expected_log.exists()
    cmd = factory.calls[0]
    for flag in ("-r", "--resume", "-c", "--continue", "--fork-session"):
        assert flag not in cmd


def test_failure_still_leaves_transcript_on_disk_ac08(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [system_line()]
    factory = FakePopenFactory(lines, returncode=1)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="implementar_historia",
    )

    with pytest.raises(RuntimeError):
        plugin.run(context)

    expected_log = workdir / ".workflow-logs" / "run-1" / "implementar_historia.log"
    assert expected_log.exists()
    assert "system" in expected_log.read_text(encoding="utf-8")


def test_transient_pattern_in_output_is_retriable(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [json.dumps({"type": "error", "message": "upstream rate_limit exceeded"}) + "\n"]
    factory = FakePopenFactory(lines, returncode=1)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="implementar_historia",
    )

    with pytest.raises(TransientError):
        plugin.run(context)


def test_result_event_reporting_is_error_is_permanent_failure(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [result_line({"summary": "falhou logicamente"}, is_error=True)]
    factory = FakePopenFactory(lines, returncode=0)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="s1",
    )

    with pytest.raises(RuntimeError):
        plugin.run(context)


def test_session_log_written_incrementally_ac02(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [
        system_line(),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}})
        + "\n",
        result_line({"summary": "done", "docs_referenced": []}),
    ]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="s1",
    )

    plugin.run(context)

    log_path = workdir / ".workflow-logs" / "run-1" / "s1.log"
    content = log_path.read_text(encoding="utf-8")
    # all 3 lines landed in the log, in order — not just the final one
    assert content.count("\n") == 3
    assert (
        content.index("subtype") < content.index("assistant") < content.index("structured_output")
    )


def test_stdin_closed_after_result_event(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [result_line({"summary": "done", "docs_referenced": []})]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="s1",
    )

    plugin.run(context)

    # A stream-json session waits for more input until stdin closes (verified
    # live) — the plugin must close it once the turn's result event arrives,
    # or the real CLI process would hang forever.
    assert factory.procs[0].stdin.closed


def test_popen_is_pinned_to_utf8_not_the_platform_default_encoding(tmp_path):
    """Regression: found running the investigar modo for real on Windows — the
    real `claude` process emits/reads UTF-8, but `text=True` alone falls back to
    locale.getpreferredencoding() (a single-byte Windows codepage in that
    environment), which raised UnicodeDecodeError on real (non-ASCII, Portuguese
    accented) output and would have silently mangled stdin prompts too.
    """
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [result_line({"summary": "ok", "docs_referenced": []})]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="s1",
    )

    plugin.run(context)

    assert factory.kwargs[0]["encoding"] == "utf-8"
    assert factory.kwargs[0]["text"] is True


def test_relative_mcp_config_path_is_resolved_against_engine_cwd_not_workspace(tmp_path):
    """Regression: found running the investigar mode for real (ADR-007) against
    ai-lup-poc-target-cli — a relative mcp_config_path must resolve against this
    process's own cwd (the motor's), never against workspace_path (the target
    repo, passed as Popen's cwd=), or the CLI fails with "MCP config file not
    found" because config/ only exists in the motor's checkout.
    """
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [result_line({"relatorio": "ok", "docs_consultados": []})]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "investigar",
            "mcp_config_path": "./config/mcp-docs-proxy.json",
            "prompt": "investigue",
            "workspace_path": str(workdir),
        },
        input_data=None,
        step_name="investigar",
    )

    plugin.run(context)

    cmd = factory.calls[0]
    resolved = cmd[cmd.index("--mcp-config") + 1]
    assert Path(resolved).is_absolute()
    assert Path(resolved) == (Path.cwd() / "config" / "mcp-docs-proxy.json").resolve()
    assert not resolved.startswith(str(workdir))


def test_investigar_mode_reads_workspace_path_from_params_ac_investigar_01(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [
        system_line(),
        result_line({"relatorio": "sem impacto relevante", "docs_consultados": ["005-x"]}),
    ]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "investigar",
            "mcp_config_path": "./config/mcp-docs-proxy.json",
            "prompt": "investigue o impacto de X",
            "docs_referenced": ["005-x"],
            "workspace_path": str(workdir),
        },
        input_data=None,
        step_name="investigar",
    )

    output = plugin.run(context)

    assert output["status"] == "success"
    assert output["relatorio"] == "sem impacto relevante"
    assert output["docs_consultados"] == ["005-x"]
    first_message = json.loads(factory.procs[0].stdin.lines[0])
    content = first_message["message"]["content"]
    assert "investigue o impacto de X" in content
    assert "005-x" in content
    # read-only: prompt explicitly forbids branch/commit/PR, not just omits them
    assert "não crie branch" in content.lower()
    assert "não abra pr" in content.lower()


def test_investigar_mode_prefers_workspace_path_from_input_when_present(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [result_line({"relatorio": "ok", "docs_consultados": []})]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "investigar",
            "mcp_config_path": "./config/mcp-docs-proxy.json",
            "prompt": "investigue",
            "workspace_path": "/should/not/be/used",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="investigar",
    )

    plugin.run(context)

    expected_log = workdir / ".workflow-logs" / "run-1" / "investigar.log"
    assert expected_log.exists()


def test_investigar_mode_without_workspace_path_raises(tmp_path):
    factory = FakePopenFactory([result_line({"relatorio": "ok", "docs_consultados": []})])
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "investigar",
            "mcp_config_path": "./config/mcp-docs-proxy.json",
            "prompt": "investigue",
        },
        input_data=None,
        step_name="investigar",
    )

    with pytest.raises(ValueError, match="workspace_path"):
        plugin.run(context)
    assert factory.calls == []


def test_coding_local_mode_reads_workspace_path_from_params_and_returns_branch_ac01_ac03(
    tmp_path,
):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [
        system_line(),
        result_line(
            {
                "summary": "implementado localmente",
                "docs_referenced": ["005-x"],
                "branch": "feature/minha-mudanca",
            }
        ),
    ]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding_local",
            "mcp_config_path": "./config/mcp-docs-proxy.json",
            "prompt": "corrija o bug X",
            "docs_referenced": ["005-x"],
            "workspace_path": str(workdir),
        },
        input_data=None,
        step_name="implementar",
    )

    output = plugin.run(context)

    assert output["status"] == "success"
    assert output["summary"] == "implementado localmente"
    assert output["docs_referenced"] == ["005-x"]
    assert output["branch"] == "feature/minha-mudanca"
    assert output["workspace_path"] == str(workdir)
    first_message = json.loads(factory.procs[0].stdin.lines[0])
    content = first_message["message"]["content"]
    assert "corrija o bug X" in content
    assert "005-x" in content
    # follows the target repo's own git workflow — never assumes a pre-created
    # branch, and never opens the PR itself (that's the target repo's own CI)
    assert "não abra a pull request" in content.lower()
    assert "nunca dê push direto" in content.lower()


def test_coding_local_mode_prefers_workspace_path_from_input_when_present(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    lines = [
        result_line({"summary": "ok", "docs_referenced": [], "branch": "feature/x"}),
    ]
    factory = FakePopenFactory(lines)
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding_local",
            "mcp_config_path": "./config/mcp-docs-proxy.json",
            "prompt": "implemente",
            "workspace_path": "/should/not/be/used",
        },
        input_data={"workspace_path": str(workdir)},
        step_name="implementar",
    )

    plugin.run(context)

    expected_log = workdir / ".workflow-logs" / "run-1" / "implementar.log"
    assert expected_log.exists()


def test_coding_local_mode_without_workspace_path_raises_ac02(tmp_path):
    factory = FakePopenFactory(
        [result_line({"summary": "ok", "docs_referenced": [], "branch": "feature/x"})]
    )
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(popen_factory=factory)

    context = make_context(
        params={
            "modo": "coding_local",
            "mcp_config_path": "./config/mcp-docs-proxy.json",
            "prompt": "implemente",
        },
        input_data=None,
        step_name="implementar",
    )

    with pytest.raises(ValueError, match="workspace_path"):
        plugin.run(context)
    assert factory.calls == []


def test_forwards_pending_instruction_to_stdin_ac04(tmp_path):
    workdir = tmp_path / "ws"
    workdir.mkdir()
    run_id, step_name = "run-1", "s1"
    instructions_path = workdir / ".workflow-logs" / run_id / f"{step_name}.instrucoes.jsonl"
    instructions_path.parent.mkdir(parents=True, exist_ok=True)
    instructions_path.write_text("pare e responda X\n", encoding="utf-8")

    lines = [system_line(), result_line({"summary": "done", "docs_referenced": []})]
    factory = FakePopenFactory(lines)
    # Short poll interval + DelayedLines' gap between lines gives the poller
    # thread real wall-clock time to notice the pre-existing instruction file
    # before the session's result event arrives.
    plugin = claude_code_runner.ClaudeCodeRunnerPlugin(
        popen_factory=factory, instruction_poll_interval=0.005
    )

    context = make_context(
        params={
            "modo": "coding",
            "mcp_config_path": "./config/mcp-docusaurus.json",
            "historia_id": "HIST-1",
        },
        input_data={"workspace_path": str(workdir)},
        run_id=run_id,
        step_name=step_name,
    )

    plugin.run(context)

    sent = [json.loads(m) for m in factory.procs[0].stdin.lines]
    contents = [m["message"]["content"] for m in sent]
    assert any("pare e responda X" in c for c in contents)
