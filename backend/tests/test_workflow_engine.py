import pytest

from tests.conftest import (
    ALWAYS_FAILS_PLUGIN_SOURCE,
    ECHO_PLUGIN_SOURCE,
    FAILING_ONCE_PLUGIN_SOURCE,
    write_plugin,
)
from workflow_engine.adapters.filesystem_plugin_registry import FileSystemPluginRegistry
from workflow_engine.adapters.sqlite_state_store import SqliteStateStore
from workflow_engine.adapters.yaml_json_chain_loader import YamlJsonChainLoader
from workflow_engine.application.retry_handler import RetryHandler
from workflow_engine.application.workflow_engine import WorkflowEngine
from workflow_engine.domain.exceptions import WorkflowFailed
from workflow_engine.domain.ports import EventLoggerPort

load_chain = YamlJsonChainLoader().load


class RecordingEventLogger(EventLoggerPort):
    def __init__(self):
        self.events: list[dict] = []

    def log_event(self, *, run_id, step_name, event, **extra):
        self.events.append({"run_id": run_id, "step_name": step_name, "event": event, **extra})


def make_engine(tmp_path, plugins_dir, event_logger=None, correlation_keys=frozenset()):
    registry = FileSystemPluginRegistry(plugins_dir)
    registry.discover()
    store = SqliteStateStore(tmp_path / "state.db")
    engine = WorkflowEngine(
        registry,
        store,
        retry_handler=RetryHandler(sleep_fn=lambda _s: None),
        event_logger=event_logger,
        correlation_keys=correlation_keys,
    )
    return engine, registry, store


def write_chain(tmp_path, name, steps_yaml):
    config = tmp_path / "chain.yaml"
    config.write_text(f"name: {name}\nsteps:\n{steps_yaml}", encoding="utf-8")
    return config


def test_new_run_executes_from_start_ac01(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    engine, registry, store = make_engine(tmp_path, plugins_dir)
    config = write_chain(
        tmp_path, "wf-1", "  - name: s1\n    plugin: echo\n    params:\n      x: 1\n"
    )
    chain = load_chain(config, known_plugins=registry.names())

    run_id = engine.run(chain, str(config))

    run = store.get_incomplete_run("wf-1")
    assert run is None  # completed, so no longer "incomplete"
    assert store.get_step_status(run_id, "s1") == "completed"


def test_output_chains_into_next_step_when_configured_ac08(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    engine, registry, store = make_engine(tmp_path, plugins_dir)
    config = write_chain(
        tmp_path,
        "wf-2",
        "  - name: s1\n    plugin: echo\n    params:\n      v: first\n"
        "  - name: s2\n    plugin: echo\n    usa_output_anterior: true\n",
    )
    chain = load_chain(config, known_plugins=registry.names())

    run_id = engine.run(chain, str(config))

    s2_output = store.get_step_output(run_id, "s2")
    s1_output = store.get_step_output(run_id, "s1")
    assert s2_output["echo"] == s1_output


def test_step_without_flag_does_not_receive_previous_output_ac09(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    engine, registry, store = make_engine(tmp_path, plugins_dir)
    config = write_chain(
        tmp_path,
        "wf-3",
        "  - name: s1\n    plugin: echo\n    params:\n      v: first\n"
        "  - name: s2\n    plugin: echo\n",
    )
    chain = load_chain(config, known_plugins=registry.names())

    run_id = engine.run(chain, str(config))

    assert store.get_step_output(run_id, "s2")["echo"] is None


def test_permanent_failure_stops_execution_ac11(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "boom.py", ALWAYS_FAILS_PLUGIN_SOURCE)
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    engine, registry, store = make_engine(tmp_path, plugins_dir)
    config = write_chain(
        tmp_path,
        "wf-4",
        "  - name: s1\n    plugin: boom\n  - name: s2\n    plugin: echo\n",
    )
    chain = load_chain(config, known_plugins=registry.names())

    with pytest.raises(WorkflowFailed):
        engine.run(chain, str(config))

    run = store.get_incomplete_run("wf-4")
    assert run is not None
    assert run.status == "failed"
    assert store.get_step_status(run.run_id, "s1") == "failed"
    assert store.get_step_status(run.run_id, "s2") is None  # never ran


def test_resume_skips_completed_steps_and_retries_failed_one_ac02(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "flaky.py", FAILING_ONCE_PLUGIN_SOURCE)
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    engine, registry, store = make_engine(tmp_path, plugins_dir)
    config = write_chain(
        tmp_path,
        "wf-5",
        "  - name: s1\n    plugin: echo\n  - name: s2\n    plugin: flaky\n",
    )
    chain = load_chain(config, known_plugins=registry.names())

    # flaky fails on its first call with no retry configured (max_attempts default = 1 for
    # the run's default policy), so the whole run fails at s2 the first time.
    with pytest.raises(WorkflowFailed):
        engine.run(chain, str(config))

    run = store.get_incomplete_run("wf-5")
    assert run is not None
    assert store.get_step_status(run.run_id, "s1") == "completed"
    assert store.get_step_status(run.run_id, "s2") == "failed"

    # Resuming re-runs s2 (now succeeds on the plugin's 2nd internal call) and does not
    # redo s1.
    run_id_2 = engine.run(chain, str(config))
    assert run_id_2 == run.run_id
    assert store.get_step_status(run_id_2, "s2") == "completed"


def test_correlation_fields_from_params_surface_on_log_events_ac16(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    logger = RecordingEventLogger()
    engine, registry, store = make_engine(
        tmp_path, plugins_dir, event_logger=logger, correlation_keys=frozenset({"historia_id"})
    )
    config = write_chain(
        tmp_path, "wf-6", "  - name: s1\n    plugin: echo\n    params:\n      historia_id: HIST-1\n"
    )
    chain = load_chain(config, known_plugins=registry.names())

    engine.run(chain, str(config))

    started = next(e for e in logger.events if e["event"] == "step_started")
    completed = next(e for e in logger.events if e["event"] == "step_completed")
    assert started["correlacao"] == {"historia_id": "HIST-1"}
    assert completed["correlacao"] == {"historia_id": "HIST-1"}


def test_no_correlacao_key_when_no_matching_field_present_ac17(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    logger = RecordingEventLogger()
    engine, registry, store = make_engine(
        tmp_path, plugins_dir, event_logger=logger, correlation_keys=frozenset({"historia_id"})
    )
    config = write_chain(tmp_path, "wf-7", "  - name: s1\n    plugin: echo\n")
    chain = load_chain(config, known_plugins=registry.names())

    engine.run(chain, str(config))

    assert all("correlacao" not in e for e in logger.events)


def test_correlation_disabled_by_default_ac19_style_backcompat(tmp_path, plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    logger = RecordingEventLogger()
    # No correlation_keys passed -> default frozenset() -> behaves like before ADR-002.
    engine, registry, store = make_engine(tmp_path, plugins_dir, event_logger=logger)
    config = write_chain(
        tmp_path, "wf-8", "  - name: s1\n    plugin: echo\n    params:\n      historia_id: HIST-1\n"
    )
    chain = load_chain(config, known_plugins=registry.names())

    engine.run(chain, str(config))

    assert all("correlacao" not in e for e in logger.events)
