import contextlib
import io
import json
import sqlite3

from tests.conftest import (
    ALWAYS_FAILS_PLUGIN_SOURCE,
    ECHO_PLUGIN_SOURCE,
    write_plugin,
)
from workflow_engine.adapters.cli import main

# A separate `run-many` invocation is a fresh process in reality (and, in these
# tests, a fresh `FileSystemPluginRegistry.discover()` — plugin modules are
# reloaded from scratch each time, so in-memory counters like
# FAILING_ONCE_PLUGIN_SOURCE's `_calls` reset on every invocation and can't
# model "fails once, then succeeds on retry" across two `run-many` calls. A
# marker *file* survives across invocations the way real state would.
FAIL_UNTIL_MARKER_PLUGIN_SOURCE = """
from pathlib import Path

from workflow_engine.plugin_sdk import Plugin, PluginContext


class FailUntilMarkerPlugin(Plugin):
    def run(self, context: PluginContext):
        marker = Path(context.params["marker_path"])
        if marker.exists():
            return {"status": "ok"}
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        raise ValueError("first attempt always fails")


PLUGIN = FailUntilMarkerPlugin
"""

CONCURRENCY_TRACKING_PLUGIN_SOURCE = """
import threading
import time

from workflow_engine.plugin_sdk import Plugin, PluginContext

_lock = threading.Lock()
_state = {"current": 0, "peak": 0}


class ConcurrencyTrackingPlugin(Plugin):
    def run(self, context: PluginContext):
        with _lock:
            _state["current"] += 1
            _state["peak"] = max(_state["peak"], _state["current"])
        time.sleep(0.1)
        with _lock:
            _state["current"] -= 1
        return {"peak_seen": _state["peak"]}


PLUGIN = ConcurrencyTrackingPlugin
"""


def write_chain(tmp_path, filename, name, plugin, step_name="s1"):
    config = tmp_path / filename
    config.write_text(
        f"name: {name}\nsteps:\n  - name: {step_name}\n    plugin: {plugin}\n",
        encoding="utf-8",
    )
    return config


def step_output(db_path):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT output FROM step_executions ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def test_runs_independent_chains_and_reports_summary_ac01_ac08(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)

    cfg1 = write_chain(tmp_path, "c1.yaml", "wf-a", "echo")
    cfg2 = write_chain(tmp_path, "c2.yaml", "wf-b", "echo")
    db_dir = tmp_path / "dbs"

    exit_code, out = _run_main(
        [
            "run-many",
            str(cfg1),
            str(cfg2),
            "--plugins-dir",
            str(plugins_dir),
            "--db-dir",
            str(db_dir),
        ]
    )

    assert exit_code == 0
    assert "wf-a" in out and "wf-b" in out
    assert "[OK]" in out
    assert "2/2 completed." in out
    assert (db_dir / "wf-a.db").exists()
    assert (db_dir / "wf-b.db").exists()


def test_duplicate_chain_name_blocks_whole_batch_before_running_ac02(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)

    cfg1 = write_chain(tmp_path, "c1.yaml", "same-name", "echo")
    cfg2 = write_chain(tmp_path, "c2.yaml", "same-name", "echo")
    db_dir = tmp_path / "dbs"

    exit_code, out = _run_main(
        [
            "run-many",
            str(cfg1),
            str(cfg2),
            "--plugins-dir",
            str(plugins_dir),
            "--db-dir",
            str(db_dir),
        ],
        capture_stderr=True,
    )

    assert exit_code == 1
    assert "duplicate chain name" in out
    # Nothing ran at all — no .db files were created for either config.
    assert not db_dir.exists() or list(db_dir.glob("*.db")) == []


def test_invalid_config_does_not_block_valid_ones_ac03(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)

    good = write_chain(tmp_path, "good.yaml", "wf-good", "echo")
    bad = write_chain(tmp_path, "bad.yaml", "wf-bad", "does-not-exist")
    db_dir = tmp_path / "dbs"

    exit_code, out = _run_main(
        [
            "run-many",
            str(good),
            str(bad),
            "--plugins-dir",
            str(plugins_dir),
            "--db-dir",
            str(db_dir),
        ]
    )

    assert exit_code == 1
    assert "[OK]     wf-good" in out
    assert "wf-bad" in out or str(bad) in out
    assert (db_dir / "wf-good.db").exists()


def test_respects_max_parallel_cap_ac04_ac05(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "tracker.py", CONCURRENCY_TRACKING_PLUGIN_SOURCE)

    configs = [write_chain(tmp_path, f"c{i}.yaml", f"wf-{i}", "tracker") for i in range(4)]
    db_dir = tmp_path / "dbs"

    exit_code, out = _run_main(
        [
            "run-many",
            *[str(c) for c in configs],
            "--plugins-dir",
            str(plugins_dir),
            "--db-dir",
            str(db_dir),
            "--max-parallel",
            "2",
        ]
    )

    assert exit_code == 0
    assert "4/4 completed." in out

    peaks = []
    for i in range(4):
        output = step_output(db_dir / f"wf-{i}.db")
        peaks.append(json.loads(output)["peak_seen"])

    # Never exceeded the configured cap...
    assert max(peaks) <= 2
    # ...but genuine concurrency did happen (not accidentally fully serial).
    assert max(peaks) == 2


def test_one_failure_does_not_cancel_others_ac09_ac10(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    write_plugin(plugins_dir, "boom.py", ALWAYS_FAILS_PLUGIN_SOURCE)

    ok_cfg = write_chain(tmp_path, "ok.yaml", "wf-ok", "echo")
    fail_cfg = write_chain(tmp_path, "fail.yaml", "wf-fail", "boom")
    db_dir = tmp_path / "dbs"

    exit_code, out = _run_main(
        [
            "run-many",
            str(ok_cfg),
            str(fail_cfg),
            "--plugins-dir",
            str(plugins_dir),
            "--db-dir",
            str(db_dir),
        ]
    )

    assert exit_code == 1
    assert "[OK]     wf-ok" in out
    assert "[FAILED] wf-fail" in out
    assert "1/2 completed." in out

    conn = sqlite3.connect(db_dir / "wf-ok.db")
    try:
        status = conn.execute("SELECT status FROM step_executions").fetchone()[0]
        assert status == "completed"
    finally:
        conn.close()


def test_isolated_state_store_survives_and_resumes_per_chain_ac06_ac07(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    write_plugin(plugins_dir, "fail_until_marker.py", FAIL_UNTIL_MARKER_PLUGIN_SOURCE)

    marker = tmp_path / "marker.flag"
    cfg_a = write_chain(tmp_path, "a.yaml", "wf-a", "echo")
    cfg_b = tmp_path / "b.yaml"
    cfg_b.write_text(
        "name: wf-b\nsteps:\n"
        "  - name: s1\n    plugin: fail_until_marker\n    params:\n"
        f"      marker_path: {marker.as_posix()}\n",
        encoding="utf-8",
    )
    db_dir = tmp_path / "dbs"
    args = [
        "run-many",
        str(cfg_a),
        str(cfg_b),
        "--plugins-dir",
        str(plugins_dir),
        "--db-dir",
        str(db_dir),
    ]

    exit_code, out = _run_main(args)
    assert exit_code == 1  # wf-b fails on its first ever attempt (no marker yet)
    assert "[OK]     wf-a" in out
    assert "[FAILED] wf-b" in out

    # Isolated files, one per chain — wf-a's own db is untouched by wf-b failing.
    assert (db_dir / "wf-a.db").exists()
    assert (db_dir / "wf-b.db").exists()
    assert marker.exists()  # proof the first attempt really ran and created it

    # Re-running the same batch resumes wf-b's failed run from the same run_id
    # (get_incomplete_run finds the "failed" run, ADR-001 semantics) — this time
    # the marker exists, so the retry of the same step succeeds.
    exit_code2, out2 = _run_main(args)
    assert exit_code2 == 0
    assert "2/2 completed." in out2


def _run_main(argv, capture_stderr=False):
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        exit_code = main(argv)
    combined = stdout_buf.getvalue() + (stderr_buf.getvalue() if capture_stderr else "")
    return exit_code, combined
