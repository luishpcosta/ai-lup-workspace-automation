import pytest

from workflow_engine.adapters.filesystem_workflow_template_registry import (
    FileSystemWorkflowTemplateRegistry,
)
from workflow_engine.domain.exceptions import WorkflowTemplateNotFoundError

VALID_TEMPLATE = """
id: investigar-impacto
label: "Investigar impacto"
description: "Investiga impacto sem PR."
params_schema:
  - name: repo_path
    label: "Repo local"
    type: select
    required: true
    source: local_repos
  - name: prompt
    label: "Prompt"
    type: textarea
    required: true

name: investigar-impacto
steps:
  - name: investigar
    plugin: claude_code_runner
    params:
      modo: investigar
"""

MISSING_ID_TEMPLATE = """
label: "Sem id"
description: "x"
name: wf
steps:
  - name: s1
    plugin: echo
"""

NOT_A_CHAIN_TEMPLATE = """
id: nao-e-chain
label: "Falta steps"
description: "x"
name: wf
"""


@pytest.fixture
def templates_dir(tmp_path):
    d = tmp_path / "templates"
    d.mkdir()
    return d


def write_template(templates_dir, filename, source):
    (templates_dir / filename).write_text(source, encoding="utf-8")


def test_discovers_valid_template_ac01(templates_dir):
    write_template(templates_dir, "investigar-impacto.yaml", VALID_TEMPLATE)

    registry = FileSystemWorkflowTemplateRegistry(templates_dir)
    discovered = registry.discover()

    assert "investigar-impacto" in discovered
    template = registry.get("investigar-impacto")
    assert template.label == "Investigar impacto"
    assert template.description == "Investiga impacto sem PR."
    assert len(template.params) == 2
    assert template.params[0].name == "repo_path"
    assert template.params[0].required is True
    assert template.params[0].source == "local_repos"
    assert template.params[1].required is True
    assert template.raw["name"] == "investigar-impacto"
    assert template.raw["steps"][0]["plugin"] == "claude_code_runner"


def test_missing_template_raises(templates_dir):
    registry = FileSystemWorkflowTemplateRegistry(templates_dir)
    registry.discover()
    with pytest.raises(WorkflowTemplateNotFoundError):
        registry.get("nope")


def test_malformed_template_is_skipped_without_breaking_others(templates_dir):
    write_template(templates_dir, "good.yaml", VALID_TEMPLATE)
    write_template(templates_dir, "missing-id.yaml", MISSING_ID_TEMPLATE)
    write_template(templates_dir, "not-a-chain.yaml", NOT_A_CHAIN_TEMPLATE)
    write_template(templates_dir, "broken.yaml", "id: [this is not valid yaml")

    registry = FileSystemWorkflowTemplateRegistry(templates_dir)
    discovered = registry.discover()

    assert set(discovered) == {"investigar-impacto"}


def test_empty_templates_dir_returns_no_templates(templates_dir):
    registry = FileSystemWorkflowTemplateRegistry(templates_dir)
    assert registry.discover() == {}
    assert registry.list() == []


def test_missing_templates_dir_does_not_raise(tmp_path):
    registry = FileSystemWorkflowTemplateRegistry(tmp_path / "does-not-exist")
    assert registry.discover() == {}
