import json

from workflow_engine.adapters.json_event_logger import JsonEventLogger


def test_log_event_emits_structured_json_ac15(capsys):
    logger = JsonEventLogger(name="test.workflow_engine.json_logger")

    logger.log_event(run_id="run-1", step_name="step-1", event="step_started")

    line = capsys.readouterr().err.strip()
    payload = json.loads(line)

    assert payload["run_id"] == "run-1"
    assert payload["step_name"] == "step-1"
    assert payload["event"] == "step_started"
    assert "timestamp" in payload
