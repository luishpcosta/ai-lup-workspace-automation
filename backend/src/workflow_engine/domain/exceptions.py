"""Domain exceptions — no infrastructure-specific error types belong here."""

from __future__ import annotations


class TransientError(Exception):
    """Raised by a plugin to signal a retriable failure.

    Any other exception raised by a plugin is treated as a permanent failure —
    the engine stops the workflow run without retrying it.
    """


class RetryExhaustedError(Exception):
    """Raised when a step exhausts its retry policy on transient failures."""

    def __init__(self, attempts: int, last_error: Exception):
        super().__init__(f"Exhausted {attempts} attempt(s); last error: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


class PluginNotFoundError(Exception):
    """Raised when the engine looks up a plugin name the registry doesn't have."""


class ChainValidationError(Exception):
    """Raised when a chain config is malformed or references an unknown plugin."""


class WorkflowFailed(Exception):
    """Raised when a step fails permanently; the run is stopped, not advanced further."""

    def __init__(self, run_id: str, step_name: str, cause: Exception):
        super().__init__(f"Run {run_id} failed at step '{step_name}': {cause}")
        self.run_id = run_id
        self.step_name = step_name
        self.cause = cause
