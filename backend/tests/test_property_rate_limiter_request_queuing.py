"""
Property-based tests for request queuing when rate limited.

Feature: ipl-live-score-integration
Property 23: Request queuing when rate limited
Validates: Requirements 7.5
"""

import asyncio

import pytest
from hypothesis import given, settings, strategies as st
from rate_limiter import RateLimiter


class FakeClock:
    """Deterministic async clock for queue timing properties."""

    def __init__(self):
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.now += delay
        await asyncio.sleep(0)


# Feature: ipl-live-score-integration, Property 23: Request queuing when rate limited
@given(
    queued_requests=st.integers(min_value=1, max_value=4),
    time_window=st.floats(min_value=0.5, max_value=2.0),
)
@settings(max_examples=10, deadline=None)
@pytest.mark.asyncio
async def test_queued_requests_execute_after_tokens_refill(queued_requests, time_window):
    """
    **Validates: Requirements 7.5**

    Property: When the rate limit has been reached, queued requests should
    wait for future token refills and then execute exactly once.
    """
    clock = FakeClock()
    limiter = RateLimiter(sleep=clock.sleep, clock=clock.monotonic)
    limiter.configure("queued_endpoint", max_requests=1, time_window=time_window)

    # Drain the initial burst token so every request below must queue.
    assert await limiter.acquire("queued_endpoint")

    execution_order = []

    async def operation(index: int) -> int:
        execution_order.append(index)
        return index

    results = await asyncio.gather(
        *[
            limiter.execute_with_limit("queued_endpoint", operation(index))
            for index in range(queued_requests)
        ]
    )

    assert results == list(range(queued_requests))
    assert execution_order == list(range(queued_requests))
    assert clock.now + 1e-9 >= time_window * queued_requests


# Feature: ipl-live-score-integration, Property 23: Request queuing when rate limited
@given(
    max_requests=st.integers(min_value=1, max_value=3),
    queued_requests=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=10, deadline=None)
@pytest.mark.asyncio
async def test_queue_request_consumes_one_token_per_queued_request(max_requests, queued_requests):
    """
    **Validates: Requirements 7.5**

    Property: Each queued request should consume exactly one token, preserving
    token accounting even when callers are waiting.
    """
    clock = FakeClock()
    limiter = RateLimiter(sleep=clock.sleep, clock=clock.monotonic)
    limiter.configure("queued_endpoint", max_requests=max_requests, time_window=1.0)

    for _ in range(max_requests):
        assert await limiter.acquire("queued_endpoint")

    await asyncio.gather(
        *[limiter.queue_request("queued_endpoint") for _ in range(queued_requests)]
    )

    available = limiter.get_available_tokens("queued_endpoint")
    assert 0 <= available < 1
