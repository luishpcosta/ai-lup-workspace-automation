import time

from fastapi.testclient import TestClient

from tests.conftest import ECHO_PLUGIN_SOURCE, write_plugin
from workflow_engine.adapters.http_api import build_app

TEMPLATE_SOURCE = """
id: tpl-echo
label: "Tpl Echo"
description: "Template de teste."
params_schema:
  - name: greeting
    label: "Greeting"
    type: text
    required: true
  - name: docs_referenced
    label: "Docs"
    type: multiselect
    required: false
    source: spec_multiselect

name: tpl-echo
steps:
  - name: s1
    plugin: echo
    params:
      greeting: "{{ vars.greeting }}"
      docs_referenced: "{{ vars.docs_referenced }}"
"""


def write_template(templates_dir, filename, source):
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / filename).write_text(source, encoding="utf-8")


def wait_for(predicate, timeout=5.0, interval=0.02):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def build_test_app(tmp_path, *, local_repos_root=None):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    templates_dir = tmp_path / "templates"
    write_template(templates_dir, "tpl-echo.yaml", TEMPLATE_SOURCE)
    watch_dir = tmp_path / "watch"
    return build_app(
        plugins_dir=str(plugins_dir),
        watch_dir=str(watch_dir),
        templates_dir=str(templates_dir),
        local_repos_root=local_repos_root,
    ), watch_dir


def test_get_workflows_lists_templates_with_schema_ac01(tmp_path):
    app, _ = build_test_app(tmp_path)
    client = TestClient(app)

    response = client.get("/workflows")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    template = body[0]
    assert template["id"] == "tpl-echo"
    assert template["label"] == "Tpl Echo"
    assert template["description"] == "Template de teste."
    names = {p["name"] for p in template["params_schema"]}
    assert names == {"greeting", "docs_referenced"}
    greeting_param = next(p for p in template["params_schema"] if p["name"] == "greeting")
    assert greeting_param["required"] is True
    docs_param = next(p for p in template["params_schema"] if p["name"] == "docs_referenced")
    assert docs_param["required"] is False
    assert docs_param["source"] == "spec_multiselect"


def test_get_local_repos_is_empty_when_not_configured_ac03(tmp_path):
    app, _ = build_test_app(tmp_path, local_repos_root=None)
    client = TestClient(app)

    response = client.get("/workspace/repos")

    assert response.status_code == 200
    assert response.json() == []


def test_get_local_repos_lists_subfolders_when_configured_ac02(tmp_path):
    repos_root = tmp_path / "repos"
    (repos_root / "ai-lup-poc-target-cli").mkdir(parents=True)
    (repos_root / "another-repo").mkdir()
    (repos_root / "not-a-repo.txt").write_text("x", encoding="utf-8")
    app, _ = build_test_app(tmp_path, local_repos_root=str(repos_root))
    client = TestClient(app)

    response = client.get("/workspace/repos")

    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert names == {"ai-lup-poc-target-cli", "another-repo"}


def test_get_local_repos_uses_root_query_param_over_configured_root_adr009_ac06(tmp_path):
    """ADR-009-AC-06: `root` troca a raiz listada sem reiniciar o processo."""
    configured_root = tmp_path / "configured"
    (configured_root / "repo-do-serve").mkdir(parents=True)
    other_root = tmp_path / "outra-arvore"
    (other_root / "repo-a").mkdir(parents=True)
    (other_root / "repo-b").mkdir()
    (other_root / "arquivo.txt").write_text("x", encoding="utf-8")
    app, _ = build_test_app(tmp_path, local_repos_root=str(configured_root))
    client = TestClient(app)

    response = client.get("/workspace/repos", params={"root": str(other_root)})

    assert response.status_code == 200
    body = response.json()
    assert {r["name"] for r in body} == {"repo-a", "repo-b"}
    assert [r["name"] for r in body] == sorted(r["name"] for r in body)
    assert all(set(r) == {"name", "path"} for r in body)


def test_get_local_repos_root_query_param_without_configured_root_adr009_ac06(tmp_path):
    """ADR-009-AC-06: `root` funciona mesmo sem raiz configurada no serve."""
    other_root = tmp_path / "arvore"
    (other_root / "repo-a").mkdir(parents=True)
    app, _ = build_test_app(tmp_path, local_repos_root=None)
    client = TestClient(app)

    response = client.get("/workspace/repos", params={"root": str(other_root)})

    assert response.status_code == 200
    assert [r["name"] for r in response.json()] == ["repo-a"]


def test_get_local_repos_missing_root_stays_empty_list_not_error_adr009_ac06(tmp_path):
    """ADR-009-AC-06: raiz inexistente responde 200 + lista vazia (semântica da AC-03)."""
    app, _ = build_test_app(tmp_path, local_repos_root=None)
    client = TestClient(app)

    response = client.get("/workspace/repos", params={"root": str(tmp_path / "nao-existe")})

    assert response.status_code == 200
    assert response.json() == []


def test_get_local_repos_without_root_param_is_unchanged_adr009_ac07(tmp_path):
    """ADR-009-AC-07: sem o parâmetro novo, a resposta é a de antes da ADR-009."""
    repos_root = tmp_path / "repos"
    (repos_root / "ai-lup-poc-target-cli").mkdir(parents=True)
    (repos_root / "another-repo").mkdir()
    app, _ = build_test_app(tmp_path, local_repos_root=str(repos_root))
    client = TestClient(app)

    response = client.get("/workspace/repos")

    assert response.status_code == 200
    assert {r["name"] for r in response.json()} == {"ai-lup-poc-target-cli", "another-repo"}


def test_post_runs_from_template_dispatches_and_completes_ac04(tmp_path):
    app, watch_dir = build_test_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/runs/from-template", json={"template_id": "tpl-echo", "params": {"greeting": "oi"}}
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "started"
    chain_name = body["chain_name"]
    assert chain_name.startswith("tpl-echo--")

    assert wait_for(lambda: (watch_dir / f"{chain_name}.db").exists())
    assert wait_for(lambda: client.get(f"/runs/{chain_name}").json().get("status") == "completed")
    detail = client.get(f"/runs/{chain_name}", params={"include": "io"}).json()
    assert detail["steps"][0]["output"]["params"]["greeting"] == "oi"


def test_post_runs_from_template_rejects_missing_required_param_ac05(tmp_path):
    app, _ = build_test_app(tmp_path)
    client = TestClient(app)

    response = client.post("/runs/from-template", json={"template_id": "tpl-echo", "params": {}})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_params"


def test_post_runs_from_template_rejects_unknown_template_ac06(tmp_path):
    app, _ = build_test_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/runs/from-template", json={"template_id": "does-not-exist", "params": {}}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "template_not_found"


def test_two_dispatches_of_the_same_template_never_collide_in_chain_name_ac07(tmp_path):
    app, watch_dir = build_test_app(tmp_path)
    client = TestClient(app)

    first = client.post(
        "/runs/from-template", json={"template_id": "tpl-echo", "params": {"greeting": "a"}}
    )
    second = client.post(
        "/runs/from-template", json={"template_id": "tpl-echo", "params": {"greeting": "b"}}
    )

    assert first.status_code == 202
    assert second.status_code == 202
    first_name = first.json()["chain_name"]
    second_name = second.json()["chain_name"]
    assert first_name != second_name
    assert wait_for(lambda: (watch_dir / f"{first_name}.db").exists())
    assert wait_for(lambda: (watch_dir / f"{second_name}.db").exists())
