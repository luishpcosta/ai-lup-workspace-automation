import pytest

from workflow_engine.application.retry_handler import RetryHandler
from workflow_engine.domain.exceptions import RetryExhaustedError, TransientError
from workflow_engine.domain.models import RetryPolicy


def test_succeeds_within_attempts_ac12():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientError("temporary")
        return "success"

    handler = RetryHandler(sleep_fn=lambda _seconds: None)
    result = handler.call(flaky, policy=RetryPolicy(max_attempts=3))

    assert result == "success"
    assert calls["n"] == 3


def test_retry_exhausted_propagates_as_failure_ac13():
    def always_transient():
        raise TransientError("still failing")

    handler = RetryHandler(sleep_fn=lambda _seconds: None)
    with pytest.raises(RetryExhaustedError):
        handler.call(always_transient, policy=RetryPolicy(max_attempts=2))


def test_non_transient_error_is_not_retried():
    calls = {"n": 0}

    def permanent():
        calls["n"] += 1
        raise ValueError("permanent")

    handler = RetryHandler(sleep_fn=lambda _seconds: None)
    with pytest.raises(ValueError):
        handler.call(permanent, policy=RetryPolicy(max_attempts=5))

    assert calls["n"] == 1


def test_on_retry_callback_invoked_per_attempt():
    attempts_seen = []

    def flaky():
        if len(attempts_seen) < 2:
            raise TransientError("x")
        return "done"

    handler = RetryHandler(sleep_fn=lambda _seconds: None)
    handler.call(
        flaky,
        policy=RetryPolicy(max_attempts=3),
        on_retry=lambda attempt, exc: attempts_seen.append(attempt),
    )

    assert attempts_seen == [1, 2]
