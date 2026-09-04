import pytest

from workflow_engine.adapters.yaml_json_chain_loader import YamlJsonChainLoader
from workflow_engine.domain.exceptions import ChainValidationError

load_chain = YamlJsonChainLoader().load


def test_loads_valid_yaml_chain_ac03(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text(
        """
name: my-workflow
steps:
  - name: step-1
    plugin: echo
    params:
      greeting: hi
  - name: step-2
    plugin: echo
    usa_output_anterior: true
""",
        encoding="utf-8",
    )

    chain = load_chain(config, known_plugins={"echo"})

    assert chain.name == "my-workflow"
    assert len(chain.steps) == 2
    assert chain.steps[0].params == {"greeting": "hi"}
    assert chain.steps[0].usa_output_anterior is False
    assert chain.steps[1].usa_output_anterior is True


def test_loads_valid_json_chain(tmp_path):
    config = tmp_path / "chain.json"
    config.write_text(
        '{"name": "wf", "steps": [{"name": "s1", "plugin": "echo"}]}', encoding="utf-8"
    )

    chain = load_chain(config, known_plugins={"echo"})

    assert chain.name == "wf"
    assert chain.steps[0].plugin == "echo"


def test_unknown_plugin_fails_before_execution_ac04(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text(
        "name: wf\nsteps:\n  - name: s1\n    plugin: does-not-exist\n", encoding="utf-8"
    )

    with pytest.raises(ChainValidationError, match="does-not-exist"):
        load_chain(config, known_plugins={"echo"})


def test_missing_config_file_raises_chain_validation_error_not_raw_os_error(tmp_path):
    with pytest.raises(ChainValidationError, match="not found"):
        load_chain(tmp_path / "does-not-exist.yaml", known_plugins={"echo"})


def test_missing_name_is_rejected(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text("steps:\n  - name: s1\n    plugin: echo\n", encoding="utf-8")

    with pytest.raises(ChainValidationError):
        load_chain(config, known_plugins={"echo"})


def test_empty_steps_is_rejected(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text("name: wf\nsteps: []\n", encoding="utf-8")

    with pytest.raises(ChainValidationError):
        load_chain(config, known_plugins={"echo"})


def test_duplicate_step_names_rejected(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text(
        "name: wf\nsteps:\n  - name: s1\n    plugin: echo\n  - name: s1\n    plugin: echo\n",
        encoding="utf-8",
    )

    with pytest.raises(ChainValidationError):
        load_chain(config, known_plugins={"echo"})


def test_retry_policy_parsed(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text(
        "name: wf\nsteps:\n"
        "  - name: s1\n    plugin: echo\n    retry:\n"
        "      max_attempts: 5\n      initial_delay: 0.5\n",
        encoding="utf-8",
    )

    chain = load_chain(config, known_plugins={"echo"})

    assert chain.steps[0].retry_policy.max_attempts == 5
    assert chain.steps[0].retry_policy.initial_delay == 0.5


def test_vars_resolved_in_step_params_ac18(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text(
        "name: wf\n"
        "vars:\n  historia_id: HIST-142\n  branch_name: feature/HIST-142\n"
        "steps:\n"
        "  - name: s1\n    plugin: echo\n    params:\n"
        "      historia_id: '{{ vars.historia_id }}'\n"
        "      title: '[{{ vars.historia_id }}] fixed'\n"
        "      labels: ['{{ vars.branch_name }}', 'automated']\n",
        encoding="utf-8",
    )

    chain = load_chain(config, known_plugins={"echo"})

    assert chain.steps[0].params["historia_id"] == "HIST-142"
    assert chain.steps[0].params["title"] == "[HIST-142] fixed"
    assert chain.steps[0].params["labels"] == ["feature/HIST-142", "automated"]


def test_config_without_vars_block_behaves_like_before_ac19(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text(
        "name: wf\nsteps:\n"
        "  - name: s1\n    plugin: echo\n    params:\n"
        "      body: 'Docs: {{ docs_referenced }}'\n",
        encoding="utf-8",
    )

    chain = load_chain(config, known_plugins={"echo"})

    # No 'vars:' block, and '{{ docs_referenced }}' has no 'vars.' prefix, so it
    # is left untouched for the plugin to resolve later from context.input.
    assert chain.steps[0].params["body"] == "Docs: {{ docs_referenced }}"


def test_unknown_vars_key_fails_validation_ac20(tmp_path):
    config = tmp_path / "chain.yaml"
    config.write_text(
        "name: wf\nvars:\n  historia_id: HIST-142\n"
        "steps:\n  - name: s1\n    plugin: echo\n    params:\n"
        "      x: '{{ vars.missing_key }}'\n",
        encoding="utf-8",
    )

    with pytest.raises(ChainValidationError, match="missing_key"):
        load_chain(config, known_plugins={"echo"})
