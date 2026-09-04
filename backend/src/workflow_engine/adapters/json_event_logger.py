"""Structured JSON logging adapter for EventLoggerPort (ADR-001, AC-15; RF-6)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from workflow_engine.domain.ports import EventLoggerPort

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()) | {"message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        return json.dumps(payload, default=str)


class JsonEventLogger(EventLoggerPort):
    """Emits one JSON object per line via the standard `logging` module."""

    def __init__(self, name: str = "workflow_engine"):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
            self._logger.propagate = False

    def log_event(self, *, run_id: str, step_name: str, event: str, **extra: Any) -> None:
        self._logger.info(event, extra={"run_id": run_id, "step_name": step_name, **extra})
