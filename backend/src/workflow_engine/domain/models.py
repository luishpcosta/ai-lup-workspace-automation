"""Value objects and entities shared across ports and the application layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetryPolicy:
    """Configurable retry policy for a single step/plugin (ADR-001, RF-5)."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    multiplier: float = 2.0

    def delay_for(self, attempt: int) -> float:
        """Backoff delay (seconds) before the given attempt number (1-indexed)."""
        if attempt <= 1:
            return 0.0
        return self.initial_delay * (self.multiplier ** (attempt - 2))


#: Applied when neither the step config nor the plugin declares a retry policy.
DEFAULT_RETRY_POLICY = RetryPolicy(max_attempts=1, initial_delay=0.0, multiplier=1.0)


@dataclass(frozen=True)
class PluginContext:
    """Input handed to a plugin's run() for a single step execution (AC-05)."""

    input: Any
    params: dict
    run_id: str
    step_name: str


@dataclass(frozen=True)
class StepDefinition:
    """One step of a chain, as declared in the chain config (AC-03)."""

    name: str
    plugin: str
    params: dict = field(default_factory=dict)
    usa_output_anterior: bool = False
    retry_policy: RetryPolicy | None = None


@dataclass(frozen=True)
class ChainDefinition:
    """A named, ordered chain of steps (RF-1)."""

    name: str
    steps: tuple[StepDefinition, ...]


@dataclass(frozen=True)
class WorkflowRun:
    """A row of workflow_runs (AC-14)."""

    run_id: str
    workflow_name: str
    config_path: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StepExecution:
    """A row of step_executions (AC-14)."""

    run_id: str
    step_name: str
    status: str
    attempt_count: int
    input: Any
    output: Any
    error_message: str | None
    started_at: str | None
    finished_at: str | None


@dataclass(frozen=True)
class WorkflowTemplateParam:
    """One entry of a template's `params_schema` (ADR-007, AT-01).

    `source` hints a driving adapter (the frontend) how to populate the field:
    `"local_repos"` (from `GET /workspace/repos`), `"spec_multiselect"` (from a
    remote docs index the frontend fetches directly), or `None` for a plain
    text/textarea field with no external data source.
    """

    name: str
    label: str
    type: str  # "text" | "textarea" | "select" | "multiselect"
    required: bool = False
    source: str | None = None


@dataclass(frozen=True)
class WorkflowTemplateDefinition:
    """A discovered workflow template (ADR-007, AT-01): a chain config file that
    also declares `id`/`label`/`description`/`params_schema`. `raw` is the full
    parsed file (name/vars/steps + metadata), reused verbatim when materializing
    a run (`application.workflow_templates.materialize_chain_raw`).
    """

    id: str
    label: str
    description: str
    params: tuple[WorkflowTemplateParam, ...]
    raw: dict
