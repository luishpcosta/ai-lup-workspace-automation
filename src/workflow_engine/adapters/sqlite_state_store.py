"""SQLite adapter for StateStorePort (ADR-001, AC-14; RF-4, RNF-04)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_engine.domain.models import WorkflowRun
from workflow_engine.domain.ports import StateStorePort

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id TEXT PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    config_path TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS step_executions (
    run_id TEXT NOT NULL REFERENCES workflow_runs(run_id),
    step_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    input TEXT,
    output TEXT,
    error_message TEXT,
    started_at TEXT,
    finished_at TEXT,
    PRIMARY KEY (run_id, step_name)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteStateStore(StateStorePort):
    """Persists workflow_runs and step_executions; supports resuming incomplete runs."""

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteStateStore:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- workflow_runs -----------------------------------------------------

    def create_run(self, run_id: str, workflow_name: str, config_path: str) -> WorkflowRun:
        now = _now()
        self._conn.execute(
            "INSERT INTO workflow_runs "
            "(run_id, workflow_name, config_path, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'running', ?, ?)",
            (run_id, workflow_name, config_path, now, now),
        )
        return WorkflowRun(run_id, workflow_name, config_path, "running", now, now)

    def get_incomplete_run(self, workflow_name: str) -> WorkflowRun | None:
        """Most recent run for workflow_name with status running or failed, if any."""
        row = self._conn.execute(
            "SELECT * FROM workflow_runs "
            "WHERE workflow_name = ? AND status IN ('running', 'failed') "
            "ORDER BY created_at DESC LIMIT 1",
            (workflow_name,),
        ).fetchone()
        return self._row_to_run(row) if row else None

    def update_run_status(self, run_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE workflow_runs SET status = ?, updated_at = ? WHERE run_id = ?",
            (status, _now(), run_id),
        )

    # -- step_executions -----------------------------------------------------

    def get_step_status(self, run_id: str, step_name: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM step_executions WHERE run_id = ? AND step_name = ?",
            (run_id, step_name),
        ).fetchone()
        return row["status"] if row else None

    def get_step_output(self, run_id: str, step_name: str) -> Any:
        row = self._conn.execute(
            "SELECT output FROM step_executions WHERE run_id = ? AND step_name = ?",
            (run_id, step_name),
        ).fetchone()
        if row is None or row["output"] is None:
            return None
        return json.loads(row["output"])

    def start_step(self, run_id: str, step_name: str, input_value: Any) -> None:
        now = _now()
        row = self._conn.execute(
            "SELECT attempt_count FROM step_executions WHERE run_id = ? AND step_name = ?",
            (run_id, step_name),
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO step_executions "
                "(run_id, step_name, status, attempt_count, input, started_at) "
                "VALUES (?, ?, 'running', 1, ?, ?)",
                (run_id, step_name, json.dumps(input_value), now),
            )
        else:
            self._conn.execute(
                "UPDATE step_executions SET status = 'running', attempt_count = ?, input = ?, "
                "started_at = ?, error_message = NULL WHERE run_id = ? AND step_name = ?",
                (row["attempt_count"] + 1, json.dumps(input_value), now, run_id, step_name),
            )

    def complete_step(self, run_id: str, step_name: str, output: Any) -> None:
        self._conn.execute(
            "UPDATE step_executions SET status = 'completed', output = ?, finished_at = ? "
            "WHERE run_id = ? AND step_name = ?",
            (json.dumps(output), _now(), run_id, step_name),
        )

    def fail_step(self, run_id: str, step_name: str, error_message: str) -> None:
        self._conn.execute(
            "UPDATE step_executions SET status = 'failed', error_message = ?, finished_at = ? "
            "WHERE run_id = ? AND step_name = ?",
            (error_message, _now(), run_id, step_name),
        )

    def _row_to_run(self, row: sqlite3.Row) -> WorkflowRun:
        return WorkflowRun(
            run_id=row["run_id"],
            workflow_name=row["workflow_name"],
            config_path=row["config_path"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
