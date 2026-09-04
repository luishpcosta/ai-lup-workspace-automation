import time

from fastapi.testclient import TestClient

from tests.conftest import ECHO_PLUGIN_SOURCE, write_plugin
from workflow_engine.adapters.cli import build_parser
from workflow_engine.adapters.filesystem_plugin_registry import FileSystemPluginRegistry
from workflow_engine.adapters.http_api import build_app
from workflow_engine.adapters.sqlite_state_store import SqliteStateStore
from workflow_engine.adapters.yaml_json_chain_loader import YamlJsonChainLoader
from workflow_engine.application.workflow_engine import WorkflowEngine

# Uses marker *files* (not in-memory threading.Event) so the test process and the
# background thread agree on state regardless of how the plugin module was loaded —
# same technique already proven in test_cli_run_many.py.
BLOCKING_PLUGIN_SOURCE = """
import time
from pathlib import Path

from workflow_engine.plugin_sdk import Plugin, PluginContext


class BlockingPlugin(Plugin):
    def run(self, context: PluginContext):
        started = Path(context.params["started_marker"])
        release = Path(context.params["release_marker"])
        started.touch()
        for _ in range(200):
            if release.exists():
                break
            time.sleep(0.02)
        return {"status": "done"}


PLUGIN = BlockingPlugin
"""


def write_chain(tmp_path, filename, name, plugin, params=None):
    lines = [f"name: {name}", "steps:", "  - name: s1", f"    plugin: {plugin}"]
    if params:
        lines.append("    params:")
        for key, value in params.items():
            lines.append(f"      {key}: {value}")
    config = tmp_path / filename
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config


def blocking_params(started, release):
    return {"started_marker": started.as_posix(), "release_marker": release.as_posix()}


def wait_for(predicate, timeout=5.0, interval=0.02):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_serve_subcommand_does_not_disturb_run_or_run_many_ac01():
    parser = build_parser()
    args = parser.parse_args(["serve", "--port", "9000"])
    assert args.command == "serve"
    assert args.port == 9000
    # Existing subcommands still parse fine (no interference from adding `serve`).
    run_args = parser.parse_args(["run", "chain.yaml"])
    assert run_args.command == "run"
    many_args = parser.parse_args(["run-many", "a.yaml", "b.yaml"])
    assert many_args.command == "run-many"


def test_post_runs_is_async_and_completes_in_background_ac02(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    config = write_chain(tmp_path, "c.yaml", "wf-a", "echo")
    watch_dir = tmp_path / "watch"

    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(watch_dir), max_parallel=2)
    client = TestClient(app)

    response = client.post("/runs", json={"config_path": str(config)})

    assert response.status_code == 202
    body = response.json()
    assert body == {"chain_name": "wf-a", "status": "started"}

    assert wait_for(lambda: (watch_dir / "wf-a.db").exists())
    assert wait_for(lambda: client.get("/runs/wf-a").json().get("status") == "completed")


def test_post_runs_rejects_invalid_config_ac03(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(tmp_path / "watch"))
    client = TestClient(app)

    response = client.post("/runs", json={"config_path": str(tmp_path / "does-not-exist.yaml")})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_config"


def test_post_runs_rejects_duplicate_concurrent_trigger_ac04(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "blocking.py", BLOCKING_PLUGIN_SOURCE)
    started = tmp_path / "started.flag"
    release = tmp_path / "release.flag"
    config = write_chain(
        tmp_path, "c.yaml", "wf-dup", "blocking", blocking_params(started, release)
    )
    watch_dir = tmp_path / "watch"
    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(watch_dir), max_parallel=2)
    client = TestClient(app)

    first = client.post("/runs", json={"config_path": str(config)})
    assert first.status_code == 202
    assert wait_for(started.exists)

    second = client.post("/runs", json={"config_path": str(config)})

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_running"

    release.touch()
    assert wait_for(lambda: client.get("/runs/wf-dup").json().get("status") == "completed")


def test_get_runs_sees_executions_from_any_source_ac05(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()

    # Simulates a run started from a terminal (`workflow run --db <watch_dir>/x.db`) —
    # created directly with the Engine, with no involvement from ServerState at all.
    registry = FileSystemPluginRegistry(plugins_dir)
    registry.discover()
    chain = YamlJsonChainLoader().load(
        str(write_chain(tmp_path, "terminal.yaml", "wf-terminal", "echo")),
        known_plugins=registry.names(),
    )
    with SqliteStateStore(watch_dir / "wf-terminal.db") as store:
        WorkflowEngine(registry, store).run(chain, "terminal.yaml")

    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(watch_dir))
    client = TestClient(app)
    api_config = write_chain(tmp_path, "api.yaml", "wf-api", "echo")
    api_resp = client.post("/runs", json={"config_path": str(api_config)})
    assert api_resp.status_code == 202
    assert wait_for(lambda: (watch_dir / "wf-api.db").exists())
    assert wait_for(lambda: client.get("/runs/wf-api").json().get("status") == "completed")

    names = {r["chain_name"] for r in client.get("/runs").json()}
    assert names == {"wf-terminal", "wf-api"}


def test_get_run_detail_hides_io_by_default_ac06(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    config = write_chain(tmp_path, "c.yaml", "wf-io", "echo")
    watch_dir = tmp_path / "watch"
    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(watch_dir))
    client = TestClient(app)

    client.post("/runs", json={"config_path": str(config)})
    assert wait_for(lambda: client.get("/runs/wf-io").json().get("status") == "completed")

    without_io = client.get("/runs/wf-io").json()
    assert "input" not in without_io["steps"][0]
    assert "output" not in without_io["steps"][0]

    with_io = client.get("/runs/wf-io", params={"include": "io"}).json()
    assert "output" in with_io["steps"][0]
    assert isinstance(with_io["steps"][0]["output"], dict)  # parsed JSON, not a raw string


def test_get_run_detail_unknown_chain_ac07(tmp_path):
    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(tmp_path / "watch"))
    client = TestClient(app)

    response = client.get("/runs/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_cancel_queued_run_succeeds_ac08(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "blocking.py", BLOCKING_PLUGIN_SOURCE)
    occupier_started = tmp_path / "occ_started.flag"
    occupier_release = tmp_path / "occ_release.flag"
    occupier = write_chain(
        tmp_path,
        "occ.yaml",
        "wf-occupier",
        "blocking",
        blocking_params(occupier_started, occupier_release),
    )
    target_started = tmp_path / "tgt_started.flag"
    target_release = tmp_path / "tgt_release.flag"
    target = write_chain(
        tmp_path,
        "tgt.yaml",
        "wf-target",
        "blocking",
        blocking_params(target_started, target_release),
    )
    watch_dir = tmp_path / "watch"
    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(watch_dir), max_parallel=1)
    client = TestClient(app)

    client.post("/runs", json={"config_path": str(occupier)})
    assert wait_for(occupier_started.exists)  # occupier now holds the only worker slot

    client.post("/runs", json={"config_path": str(target)})
    # target can't have started yet — pool size is 1 and occupier hasn't released.
    assert not target_started.exists()

    cancel_resp = client.post("/runs/wf-target/cancelar")

    assert cancel_resp.status_code == 200
    assert cancel_resp.json() == {"chain_name": "wf-target", "status": "cancelled"}

    occupier_release.touch()
    assert wait_for(lambda: client.get("/runs/wf-occupier").json().get("status") == "completed")
    # target genuinely never ran — cancelled before Future started, per stdlib guarantee.
    assert not target_started.exists()
    assert not (watch_dir / "wf-target.db").exists()


def test_cancel_running_run_is_refused_honestly_ac09(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "blocking.py", BLOCKING_PLUGIN_SOURCE)
    started = tmp_path / "started.flag"
    release = tmp_path / "release.flag"
    config = write_chain(
        tmp_path, "c.yaml", "wf-running", "blocking", blocking_params(started, release)
    )
    watch_dir = tmp_path / "watch"
    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(watch_dir), max_parallel=2)
    client = TestClient(app)

    client.post("/runs", json={"config_path": str(config)})
    assert wait_for(started.exists)

    response = client.post("/runs/wf-running/cancelar")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_running"

    release.touch()
    assert wait_for(lambda: client.get("/runs/wf-running").json().get("status") == "completed")


def test_cancel_run_from_another_process_is_refused_ac09b(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()

    registry = FileSystemPluginRegistry(plugins_dir)
    registry.discover()
    chain = YamlJsonChainLoader().load(
        str(write_chain(tmp_path, "terminal.yaml", "wf-foreign", "echo")),
        known_plugins=registry.names(),
    )
    with SqliteStateStore(watch_dir / "wf-foreign.db") as store:
        WorkflowEngine(registry, store).run(chain, "terminal.yaml")

    app = build_app(plugins_dir=str(plugins_dir), watch_dir=str(watch_dir))
    client = TestClient(app)

    response = client.post("/runs/wf-foreign/cancelar")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_cancellable"


def test_cancel_unknown_chain_ac10(tmp_path):
    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(tmp_path / "watch"))
    client = TestClient(app)

    response = client.post("/runs/does-not-exist/cancelar")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
