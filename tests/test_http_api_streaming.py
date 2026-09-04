import threading
import time

from fastapi.testclient import TestClient

from workflow_engine.adapters.http_api import build_app
from workflow_engine.adapters.sqlite_state_store import SqliteStateStore


def write_chain(tmp_path, filename, name, plugin, params=None):
    lines = [f"name: {name}", "steps:", "  - name: s1", f"    plugin: {plugin}"]
    if params:
        lines.append("    params:")
        for key, value in params.items():
            lines.append(f"      {key}: {value}")
    config = tmp_path / filename
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config


def seed_running_claude_step(watch_dir, tmp_path, chain_name, workdir, run_id="run-1"):
    """Simulates a run already in progress — created directly with SqliteStateStore,
    the same way a `workflow run`/`run-many` process in a terminal would, with no
    involvement from ServerState at all (ADR-005, AC-10: the mechanism must not care
    who started the run).
    """
    config = write_chain(
        tmp_path,
        f"{chain_name}.yaml",
        chain_name,
        "claude_code_runner",
        params={"modo": "coding", "mcp_config_path": "x", "historia_id": "H1"},
    )
    db_file = watch_dir / f"{chain_name}.db"
    with SqliteStateStore(db_file) as store:
        store.create_run(run_id, chain_name, str(config))
        store.start_step(run_id, "s1", {"workspace_path": str(workdir)})
    return db_file


def test_stream_tails_active_claude_step_live_and_stops_on_completion_ac06(tmp_path):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    db_file = seed_running_claude_step(watch_dir, tmp_path, "wf-stream", workdir)

    log_path = workdir / ".workflow-logs" / "run-1" / "s1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('{"type": "system", "subtype": "init"}\n', encoding="utf-8")

    def append_then_complete():
        time.sleep(0.15)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write('{"type": "assistant", "text": "hi"}\n')
        time.sleep(0.15)
        with SqliteStateStore(db_file) as store:
            store.complete_step("run-1", "s1", {"status": "success"})

    thread = threading.Thread(target=append_then_complete)
    thread.start()

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    with client.stream("GET", "/runs/wf-stream/stream") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    thread.join(timeout=5)

    assert '"type": "system"' in body
    assert '"type": "assistant"' in body


def test_stream_refuses_when_no_active_claude_step_ac07(tmp_path):
    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(tmp_path / "watch"))
    client = TestClient(app)

    response = client.get("/runs/does-not-exist/stream")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_streamable"


def test_post_instruction_appends_to_deterministic_file_ac08(tmp_path):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    seed_running_claude_step(watch_dir, tmp_path, "wf-instr", workdir)

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    response = client.post("/runs/wf-instr/instrucoes", json={"mensagem": "pare agora"})

    assert response.status_code == 202
    assert response.json() == {"chain_name": "wf-instr", "status": "accepted"}
    instructions_path = workdir / ".workflow-logs" / "run-1" / "s1.instrucoes.jsonl"
    assert instructions_path.exists()
    assert "pare agora" in instructions_path.read_text(encoding="utf-8")


def test_post_instruction_refuses_when_no_active_claude_step_ac09(tmp_path):
    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(tmp_path / "watch"))
    client = TestClient(app)

    response = client.post("/runs/does-not-exist/instrucoes", json={"mensagem": "x"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_interactable"


# Note on AC-10 (mechanism works the same regardless of who started the run):
# every test above already seeds its run via `seed_running_claude_step`, which
# uses `SqliteStateStore` directly — the same way a terminal-triggered
# `workflow run`/`run-many` would, never through `ServerState.trigger()`. A
# dedicated AC-10 test that also *opens* the stream would need to complete the
# step to let the generator terminate (TestClient's ASGI transport runs a sync
# generator to completion before returning from `client.stream()`, so an
# open-ended one — nothing here ever calls complete_step — hangs forever);
# that's exactly what AC-06 already does, so a separate test would just repeat it.
