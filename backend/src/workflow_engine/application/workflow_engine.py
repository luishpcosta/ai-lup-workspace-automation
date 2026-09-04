"""Sequential orchestration of a chain's steps (ADR-001, AC-08..AC-11; RF-4, RF-7).

Depends only on ports (`workflow_engine.domain.ports`) — never on a concrete
adapter. The composition root (`workflow_engine.adapters.cli`) decides which
StateStore/PluginRegistry/EventLogger implementation to inject.

Also emits correlation fields on log events (ADR-002, AC-16/AC-17; RNF-1).
`JsonEventLogger` already passes through any `**extra` it's given — the only
piece missing was *deciding* which fields to surface, which lives here so the
engine stays plugin-agnostic: `correlation_keys` is an opaque set of field
names supplied by the composition root (`cli.py`), not hardcoded knowledge of
any specific plugin's params (e.g. `historia_id`, `pr_number` from ADR-002
never appear as literals in this module).
"""

from __future__ import annotations

import uuid
from typing import Any

from workflow_engine.application.retry_handler import RetryHandler
from workflow_engine.domain.exceptions import WorkflowFailed
from workflow_engine.domain.models import DEFAULT_RETRY_POLICY, ChainDefinition, PluginContext
from workflow_engine.domain.ports import (
    EventLoggerPort,
    NullEventLogger,
    PluginRegistryPort,
    StateStorePort,
)


class WorkflowEngine:
    """Runs a ChainDefinition step by step, persisting progress and applying retry."""

    def __init__(
        self,
        registry: PluginRegistryPort,
        state_store: StateStorePort,
        retry_handler: RetryHandler | None = None,
        event_logger: EventLoggerPort | None = None,
        correlation_keys: frozenset[str] = frozenset(),
    ):
        self._registry = registry
        self._state_store = state_store
        self._retry_handler = retry_handler or RetryHandler()
        self._event_logger = event_logger or NullEventLogger()
        self._correlation_keys = correlation_keys

    def run(self, chain: ChainDefinition, config_path: str) -> str:
        run = self._state_store.get_incomplete_run(chain.name)
        if run is None:
            run_id = str(uuid.uuid4())
            self._state_store.create_run(run_id, chain.name, str(config_path))
        else:
            run_id = run.run_id

        previous_output: Any = None
        for step in chain.steps:
            status = self._state_store.get_step_status(run_id, step.name)
            if status == "completed":
                previous_output = self._state_store.get_step_output(run_id, step.name)
                continue

            input_value = previous_output if step.usa_output_anterior else None
            self._state_store.start_step(run_id, step.name, input_value)
            self._log(run_id, step.name, "step_started", step.params, input_value)

            plugin = self._registry.get(step.plugin)
            context = PluginContext(
                input=input_value, params=step.params, run_id=run_id, step_name=step.name
            )
            policy = step.retry_policy or plugin.default_retry_policy or DEFAULT_RETRY_POLICY

            def on_retry(attempt: int, exc: Exception, _step=step, _input=input_value) -> None:
                self._log(
                    run_id,
                    _step.name,
                    "step_retry",
                    _step.params,
                    _input,
                    attempt=attempt,
                    error=str(exc),
                )

            try:
                output = self._retry_handler.call(
                    lambda _plugin=plugin, _context=context: _plugin.run(_context),
                    policy=policy,
                    on_retry=on_retry,
                )
            except Exception as exc:  # noqa: BLE001 - any exception here is a permanent failure
                self._state_store.fail_step(run_id, step.name, str(exc))
                self._state_store.update_run_status(run_id, "failed")
                self._log(
                    run_id, step.name, "step_failed", step.params, input_value, error=str(exc)
                )
                raise WorkflowFailed(run_id, step.name, exc) from exc

            self._state_store.complete_step(run_id, step.name, output)
            self._log(run_id, step.name, "step_completed", step.params, output)
            previous_output = output

        self._state_store.update_run_status(run_id, "completed")
        self._event_logger.log_event(run_id=run_id, step_name="-", event="workflow_completed")
        return run_id

    def _log(
        self, run_id: str, step_name: str, event: str, *correlation_sources: Any, **extra: Any
    ) -> None:
        """Emit a log event, adding a 'correlacao' extra when any configured
        correlation key is present in the given sources (ADR-002, AC-16/AC-17).
        """
        correlacao = self._correlation(*correlation_sources)
        if correlacao:
            extra["correlacao"] = correlacao
        self._event_logger.log_event(run_id=run_id, step_name=step_name, event=event, **extra)

    def _correlation(self, *sources: Any) -> dict:
        found: dict = {}
        for source in sources:
            if not isinstance(source, dict):
                continue
            for key in self._correlation_keys:
                if key in source:
                    found[key] = source[key]
        return found
