"""Unit tests for RetryPolicy exponential backoff logic."""

from __future__ import annotations


import pytest

from backend.app.services.retry_policy import (
    ErrorCategory,
    RetryPolicy,
    RetryRemedy,
)


@pytest.fixture()
def policy() -> RetryPolicy:
    return RetryPolicy(max_attempts=3, base_delay_seconds=0.01)


def test_classify_network_error(policy: RetryPolicy) -> None:
    exc = TimeoutError("Connection timed out")
    category = policy.classify_error(exc)
    assert category == ErrorCategory.TRANSIENT_NETWORK


def test_classify_auth_error(policy: RetryPolicy) -> None:
    exc = PermissionError("Access denied")
    category = policy.classify_error(exc)
    assert category == ErrorCategory.AUTH_FAILURE


def test_classify_disk_error(policy: RetryPolicy) -> None:
    exc = OSError("No space left on device")
    category = policy.classify_error(exc)
    assert category == ErrorCategory.IO_ERROR


def test_calculate_backoff_increases_exponentially(policy: RetryPolicy) -> None:
    delay_1 = policy.calculate_backoff(1, ErrorCategory.TRANSIENT_NETWORK)
    delay_2 = policy.calculate_backoff(2, ErrorCategory.TRANSIENT_NETWORK)
    delay_3 = policy.calculate_backoff(3, ErrorCategory.TRANSIENT_NETWORK)
    assert delay_1 < delay_2 < delay_3
    assert delay_2 >= delay_1 * 2


def test_calculate_backoff_caps_at_max(policy: RetryPolicy) -> None:
    delay = policy.calculate_backoff(10, ErrorCategory.TRANSIENT_NETWORK)
    assert delay <= policy._max_delay


@pytest.mark.asyncio
async def test_execute_with_retry_succeeds_eventually(policy: RetryPolicy) -> None:
    call_count = 0

    async def work_eventually_succeeds() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise TimeoutError("Temporary failure")
        return "success"

    result = await policy.execute_with_retry(work_eventually_succeeds)
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_execute_with_retry_exhausts_attempts(policy: RetryPolicy) -> None:
    async def always_fails() -> str:
        raise RuntimeError("Permanent failure")

    with pytest.raises(RuntimeError):
        await policy.execute_with_retry(always_fails)
    assert policy.attempt_count == policy.max_attempts


@pytest.mark.asyncio
async def test_execute_with_retry_invokes_callback(policy: RetryPolicy) -> None:
    remedies: list[RetryRemedy] = []

    async def capture_remedy(remedy: RetryRemedy) -> None:
        remedies.append(remedy)

    async def fail_once() -> str:
        if policy.attempt_count < 2:
            raise TimeoutError("Retry me")
        return "ok"

    result = await policy.execute_with_retry(fail_once, on_retry=capture_remedy)
    assert result == "ok"
    assert len(remedies) == 1
    assert remedies[0].category == ErrorCategory.TRANSIENT_NETWORK


def test_attempts_remaining(policy: RetryPolicy) -> None:
    assert policy.attempts_remaining == policy.max_attempts
    policy._attempt_count = 1
    assert policy.attempts_remaining == 2
    policy._attempt_count = 3
    assert policy.attempts_remaining == 0
