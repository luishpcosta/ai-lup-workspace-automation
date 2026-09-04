from tests.conftest import ECHO_PLUGIN_SOURCE, write_plugin
from workflow_engine.adapters.cli import main


def test_cli_runs_workflow_end_to_end(tmp_path, capsys):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)

    config = tmp_path / "chain.yaml"
    config.write_text("name: cli-wf\nsteps:\n  - name: s1\n    plugin: echo\n", encoding="utf-8")

    db_path = tmp_path / "state.db"
    exit_code = main(["run", str(config), "--plugins-dir", str(plugins_dir), "--db", str(db_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "cli-wf" in out
    assert "completed" in out


def test_cli_reports_invalid_config(tmp_path, capsys):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    config = tmp_path / "chain.yaml"
    config.write_text(
        "name: cli-wf\nsteps:\n  - name: s1\n    plugin: does-not-exist\n", encoding="utf-8"
    )

    exit_code = main(
        ["run", str(config), "--plugins-dir", str(plugins_dir), "--db", str(tmp_path / "state.db")]
    )

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "does-not-exist" in err
