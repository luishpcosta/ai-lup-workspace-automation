import threading
import time

from fastapi.testclient import TestClient

from workflow_engine.adapters.http_api import build_app
from workflow_engine.adapters.sqlite_state_store import SqliteStateStore
from workflow_engine.adapters.yaml_json_chain_loader import YamlJsonChainLoader


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


def test_stream_resolves_workspace_path_from_step_params_for_investigar_modo(tmp_path):
    """Regression (ADR-007): found running the `investigar` modo for real against
    a live SSE stream. `investigar` has no preceding workspace_setup step, so
    there is no carry-forward `input` — workspace_path only exists in the step's
    own `params`. Before this fix, `_resolve_active_claude_step` only ever
    looked at `input`, so /stream and /instrucoes always answered 409 for this
    modo, even with a genuinely running claude_code_runner step.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    config = write_chain(
        tmp_path,
        "wf-investigar.yaml",
        "wf-investigar",
        "claude_code_runner",
        params={
            "modo": "investigar",
            "mcp_config_path": "x",
            "prompt": "y",
            "workspace_path": str(workdir),
        },
    )
    db_file = watch_dir / "wf-investigar.db"
    with SqliteStateStore(db_file) as store:
        store.create_run("run-1", "wf-investigar", str(config))
        store.start_step("run-1", "s1", None)  # no carry-forward input at all

    log_path = workdir / ".workflow-logs" / "run-1" / "s1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('{"type": "system", "subtype": "init"}\n', encoding="utf-8")

    def complete_shortly():
        time.sleep(0.15)
        with SqliteStateStore(db_file) as store:
            store.complete_step("run-1", "s1", {"status": "success"})

    thread = threading.Thread(target=complete_shortly)
    thread.start()

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    with client.stream("GET", "/runs/wf-investigar/stream") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    thread.join(timeout=5)

    assert '"type": "system"' in body


def test_post_instruction_resolves_workspace_path_from_step_params_for_investigar_modo(tmp_path):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    config = write_chain(
        tmp_path,
        "wf-investigar.yaml",
        "wf-investigar",
        "claude_code_runner",
        params={
            "modo": "investigar",
            "mcp_config_path": "x",
            "prompt": "y",
            "workspace_path": str(workdir),
        },
    )
    with SqliteStateStore(watch_dir / "wf-investigar.db") as store:
        store.create_run("run-1", "wf-investigar", str(config))
        store.start_step("run-1", "s1", None)

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    response = client.post("/runs/wf-investigar/instrucoes", json={"mensagem": "pare agora"})

    assert response.status_code == 202
    instructions_path = workdir / ".workflow-logs" / "run-1" / "s1.instrucoes.jsonl"
    assert instructions_path.exists()
    assert "pare agora" in instructions_path.read_text(encoding="utf-8")


def test_post_instruction_refuses_when_no_active_claude_step_ac09(tmp_path):
    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(tmp_path / "watch"))
    client = TestClient(app)

    response = client.post("/runs/does-not-exist/instrucoes", json={"mensagem": "x"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_interactable"


def test_post_answer_writes_deterministic_resposta_file(tmp_path):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    seed_running_claude_step(watch_dir, tmp_path, "wf-resposta", workdir)

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    response = client.post(
        "/runs/wf-resposta/resposta", json={"resposta": "use a branch feature/x"}
    )

    assert response.status_code == 202
    assert response.json() == {"chain_name": "wf-resposta", "status": "accepted"}
    resposta_path = workdir / ".workflow-logs" / "run-1" / "s1.resposta.json"
    assert resposta_path.exists()
    assert resposta_path.read_text(encoding="utf-8") == "use a branch feature/x"


def test_post_answer_overwrites_previous_pending_answer(tmp_path):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    seed_running_claude_step(watch_dir, tmp_path, "wf-resposta2", workdir)

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    client.post("/runs/wf-resposta2/resposta", json={"resposta": "primeira"})
    client.post("/runs/wf-resposta2/resposta", json={"resposta": "segunda"})

    resposta_path = workdir / ".workflow-logs" / "run-1" / "s1.resposta.json"
    # overwrite, not append: at most one pending question per step (ask_user
    # blocks the agent, so it can't ask a second one before the first is
    # answered)
    assert resposta_path.read_text(encoding="utf-8") == "segunda"


def test_awaiting_input_true_while_pergunta_file_exists_adr013(tmp_path):
    """ADR-013: GET /runs and GET /runs/{chain_name} report `awaiting_input`
    purely from the existence of the step's `.pergunta.json` (written by
    mcp_servers/ask_user_server.py while an `ask_user` call is pending) — no DB
    status change, same "derived from a file, at read time" mechanism already
    used by `/stream`/`/instrucoes`.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    seed_running_claude_step(watch_dir, tmp_path, "wf-awaiting", workdir)

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    assert client.get("/runs/wf-awaiting").json()["awaiting_input"] is False
    assert (
        next(r for r in client.get("/runs").json() if r["chain_name"] == "wf-awaiting")[
            "awaiting_input"
        ]
        is False
    )

    pergunta_path = workdir / ".workflow-logs" / "run-1" / "s1.pergunta.json"
    pergunta_path.parent.mkdir(parents=True, exist_ok=True)
    pergunta_path.write_text('{"question": "Qual branch?", "options": []}', encoding="utf-8")

    assert client.get("/runs/wf-awaiting").json()["awaiting_input"] is True
    assert (
        next(r for r in client.get("/runs").json() if r["chain_name"] == "wf-awaiting")[
            "awaiting_input"
        ]
        is True
    )

    pergunta_path.unlink()

    assert client.get("/runs/wf-awaiting").json()["awaiting_input"] is False


def test_awaiting_input_false_for_terminal_run_even_with_leftover_pergunta_file(tmp_path):
    """A stale .pergunta.json (e.g. left behind by a crash) never resurrects
    awaiting_input once the run itself isn't `running` any more — the `status ==
    "running"` guard short-circuits before any file check.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    db_file = seed_running_claude_step(watch_dir, tmp_path, "wf-awaiting-done", workdir)

    pergunta_path = workdir / ".workflow-logs" / "run-1" / "s1.pergunta.json"
    pergunta_path.parent.mkdir(parents=True, exist_ok=True)
    pergunta_path.write_text('{"question": "Qual branch?", "options": []}', encoding="utf-8")

    with SqliteStateStore(db_file) as store:
        store.complete_step("run-1", "s1", {"status": "success"})
        store.update_run_status("run-1", "completed")

    assert client_awaiting_input(watch_dir, "wf-awaiting-done") is False


def client_awaiting_input(watch_dir, chain_name):
    app = build_app(plugins_dir=str(watch_dir.parent / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)
    return client.get(f"/runs/{chain_name}").json()["awaiting_input"]


def test_get_run_detail_loads_chain_yaml_only_once_per_request_adr013(tmp_path, monkeypatch):
    """Regression (code review, ADR-013): `get_run_detail` used to reload the
    chain YAML twice per request against a running chain — once for `plugin`
    per step, once more inside `_is_awaiting_input`/`_resolve_active_claude_step`
    — plus a redundant workflow_runs/step_executions round trip. Both now share
    one already-loaded `chain` object.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    workdir = tmp_path / "ws"
    workdir.mkdir()
    seed_running_claude_step(watch_dir, tmp_path, "wf-single-load", workdir)

    call_count = 0
    original_load = YamlJsonChainLoader.load

    def counting_load(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_load(self, *args, **kwargs)

    monkeypatch.setattr(YamlJsonChainLoader, "load", counting_load)

    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(watch_dir))
    client = TestClient(app)

    response = client.get("/runs/wf-single-load")

    assert response.status_code == 200
    assert response.json()["steps"][0]["plugin"] == "claude_code_runner"
    assert call_count == 1


def test_post_answer_refuses_when_no_active_claude_step(tmp_path):
    app = build_app(plugins_dir=str(tmp_path / "plugins"), watch_dir=str(tmp_path / "watch"))
    client = TestClient(app)

    response = client.post("/runs/does-not-exist/resposta", json={"resposta": "x"})

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
