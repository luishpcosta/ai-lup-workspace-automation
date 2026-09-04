"""Ports: the interfaces the hexagon depends on. Adapters implement these.

- `Plugin` is the driven port that plugin authors implement (the engine calls
  out to it) — it is also the extension point described in ADR-001.
- `PluginRegistryPort`, `StateStorePort`, `EventLoggerPort` are driven ports the
  application layer (`workflow_engine.application`) depends on.
- `ChainLoaderPort` is a driven port consumed by a driving adapter (the CLI)
  rather than by the application core itself — it exists so the composition
  root can swap the config format (YAML/JSON today, something else tomorrow)
  without the CLI knowing the concrete parser.

No infrastructure imports here — only `abc` and domain models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from workflow_engine.domain.models import (
    ChainDefinition,
    PluginContext,
    RetryPolicy,
    WorkflowRun,
)


class Plugin(ABC):
    """Base class every plugin must implement to be recognized by the engine."""

    #: Optional default retry policy for this plugin; a step's own config overrides it.
    default_retry_policy: RetryPolicy | None = None

    @abstractmethod
    def run(self, context: PluginContext) -> Any:
        """Execute the step. Return a JSON-serializable output.

        Raise TransientError for a retriable failure; raise anything else for a
        permanent failure.
        """
        raise NotImplementedError


class PluginRegistryPort(ABC):
    """Resolves plugin instances by name (RF-3)."""

    @abstractmethod
    def discover(self) -> dict[str, Plugin]:
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str) -> Plugin:
        raise NotImplementedError

    @abstractmethod
    def names(self) -> set[str]:
        raise NotImplementedError


class StateStorePort(ABC):
    """Persists workflow/step progress and supports resuming (RF-4, AC-14)."""

    @abstractmethod
    def create_run(self, run_id: str, workflow_name: str, config_path: str) -> WorkflowRun:
        raise NotImplementedError

    @abstractmethod
    def get_incomplete_run(self, workflow_name: str) -> WorkflowRun | None:
        raise NotImplementedError

    @abstractmethod
    def update_run_status(self, run_id: str, status: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_step_status(self, run_id: str, step_name: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def get_step_output(self, run_id: str, step_name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def start_step(self, run_id: str, step_name: str, input_value: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def complete_step(self, run_id: str, step_name: str, output: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def fail_step(self, run_id: str, step_name: str, error_message: str) -> None:
        raise NotImplementedError


class EventLoggerPort(ABC):
    """Emits structured execution events (RF-6, AC-15)."""

    @abstractmethod
    def log_event(self, *, run_id: str, step_name: str, event: str, **extra: Any) -> None:
        raise NotImplementedError


class NullEventLogger(EventLoggerPort):
    """No-op logger, so the application layer can default to *something* without
    importing a concrete adapter — composition roots pass a real one in.
    """

    def log_event(self, *, run_id: str, step_name: str, event: str, **extra: Any) -> None:
        return None


class ChainLoaderPort(ABC):
    """Builds a ChainDefinition from an external source (RF-1, AC-03/AC-04)."""

    @abstractmethod
    def load(self, source: str, known_plugins: set[str] | None = None) -> ChainDefinition:
        raise NotImplementedError
