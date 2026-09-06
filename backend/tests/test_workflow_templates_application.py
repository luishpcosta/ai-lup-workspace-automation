from workflow_engine.application.workflow_templates import (
    materialize_chain_raw,
    validate_params,
)
from workflow_engine.domain.models import WorkflowTemplateDefinition, WorkflowTemplateParam


def make_template(**overrides):
    defaults = dict(
        id="investigar-impacto",
        label="Investigar impacto",
        description="x",
        params=(
            WorkflowTemplateParam(name="repo_path", label="Repo", type="select", required=True),
            WorkflowTemplateParam(name="prompt", label="Prompt", type="textarea", required=True),
            WorkflowTemplateParam(
                name="docs_referenced", label="Docs", type="multiselect", required=False
            ),
        ),
        raw={
            "id": "investigar-impacto",
            "name": "investigar-impacto",
            "steps": [{"name": "s1", "plugin": "claude_code_runner", "params": {}}],
        },
    )
    defaults.update(overrides)
    return WorkflowTemplateDefinition(**defaults)


def test_validate_params_reports_missing_required_fields():
    template = make_template()

    errors = validate_params(template, {"repo_path": "/repos/x"})

    assert any("prompt" in e for e in errors)
    assert not any("repo_path" in e for e in errors)


def test_validate_params_passes_when_all_required_present():
    template = make_template()

    errors = validate_params(template, {"repo_path": "/repos/x", "prompt": "investigue X"})

    assert errors == []


def test_validate_params_ignores_missing_optional_field():
    template = make_template()

    errors = validate_params(template, {"repo_path": "/repos/x", "prompt": "investigue X"})

    assert errors == []


def test_materialize_chain_raw_renames_chain_and_merges_vars():
    template = make_template()

    raw = materialize_chain_raw(
        template,
        {"repo_path": "/repos/x", "prompt": "investigue X", "docs_referenced": ["005-a", "004-b"]},
        chain_name="investigar-impacto--abc123",
    )

    assert raw["name"] == "investigar-impacto--abc123"
    assert raw["vars"]["repo_path"] == "/repos/x"
    assert raw["vars"]["prompt"] == "investigue X"
    # list type is preserved, not stringified
    assert raw["vars"]["docs_referenced"] == ["005-a", "004-b"]
    # original template.raw is not mutated
    assert "vars" not in template.raw


def test_materialize_chain_raw_defaults_unsubmitted_optional_params_to_empty_string():
    template = make_template()

    raw = materialize_chain_raw(
        template, {"repo_path": "/repos/x", "prompt": "investigue X"}, chain_name="c1"
    )

    # docs_referenced was optional and not submitted — defaults to "" so
    # `{{ vars.docs_referenced }}` in a step still resolves (Chain Loader
    # validation fails before execution otherwise), same falsy behavior a
    # plugin would see from an omitted param.
    assert raw["vars"]["docs_referenced"] == ""
