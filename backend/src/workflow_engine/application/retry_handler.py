"""Retry orchestration for transient failures (ADR-001, AC-12/AC-13)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from workflow_engine.domain.exceptions import RetryExhaustedError, TransientError
from workflow_engine.domain.models import DEFAULT_RETRY_POLICY, RetryPolicy

T = TypeVar("T")


class RetryHandler:
    """Wraps a plugin call, retrying on TransientError per the step's RetryPolicy."""

    def __init__(self, sleep_fn: Callable[[float], None] = time.sleep):
        self._sleep = sleep_fn

    def call(
        self,
        fn: Callable[[], T],
        policy: RetryPolicy | None = None,
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> T:
        """Call fn(), retrying only on TransientError, up to policy.max_attempts.

        Any non-transient exception propagates immediately without retry.
        """
        policy = policy or DEFAULT_RETRY_POLICY
        last_error: Exception | None = None
        for attempt in range(1, policy.max_attempts + 1):
            if attempt > 1:
                self._sleep(policy.delay_for(attempt))
            try:
                return fn()
            except TransientError as exc:
                last_error = exc
                if on_retry is not None:
                    on_retry(attempt, exc)
                continue
        assert last_error is not None
        raise RetryExhaustedError(policy.max_attempts, last_error) from last_error
