from workflow_engine.adapters.sqlite_state_store import SqliteStateStore


def test_create_run_and_lookup(tmp_path):
    with SqliteStateStore(tmp_path / "state.db") as store:
        run = store.create_run("run-1", "wf", "config.yaml")
        assert run.status == "running"

        incomplete = store.get_incomplete_run("wf")
        assert incomplete is not None
        assert incomplete.run_id == "run-1"


def test_no_incomplete_run_for_unknown_workflow(tmp_path):
    with SqliteStateStore(tmp_path / "state.db") as store:
        assert store.get_incomplete_run("nonexistent") is None


def test_completed_run_is_not_incomplete(tmp_path):
    with SqliteStateStore(tmp_path / "state.db") as store:
        store.create_run("run-1", "wf", "config.yaml")
        store.update_run_status("run-1", "completed")
        assert store.get_incomplete_run("wf") is None


def test_failed_run_is_incomplete_and_resumable(tmp_path):
    with SqliteStateStore(tmp_path / "state.db") as store:
        store.create_run("run-1", "wf", "config.yaml")
        store.update_run_status("run-1", "failed")
        incomplete = store.get_incomplete_run("wf")
        assert incomplete is not None
        assert incomplete.status == "failed"


def test_step_lifecycle_persists_output_before_next_step_ac10(tmp_path):
    with SqliteStateStore(tmp_path / "state.db") as store:
        store.create_run("run-1", "wf", "config.yaml")
        store.start_step("run-1", "step-a", input_value=None)
        assert store.get_step_status("run-1", "step-a") == "running"

        store.complete_step("run-1", "step-a", {"result": 42})
        assert store.get_step_status("run-1", "step-a") == "completed"
        assert store.get_step_output("run-1", "step-a") == {"result": 42}


def test_step_failure_recorded_ac11(tmp_path):
    with SqliteStateStore(tmp_path / "state.db") as store:
        store.create_run("run-1", "wf", "config.yaml")
        store.start_step("run-1", "step-a", input_value=None)
        store.fail_step("run-1", "step-a", "boom")
        assert store.get_step_status("run-1", "step-a") == "failed"


def test_restarting_a_step_increments_attempt_count(tmp_path):
    with SqliteStateStore(tmp_path / "state.db") as store:
        store.create_run("run-1", "wf", "config.yaml")
        store.start_step("run-1", "step-a", input_value=None)
        store.fail_step("run-1", "step-a", "boom")
        store.start_step("run-1", "step-a", input_value=None)

        row = store._conn.execute(
            "SELECT attempt_count FROM step_executions WHERE run_id = ? AND step_name = ?",
            ("run-1", "step-a"),
        ).fetchone()
        assert row["attempt_count"] == 2
