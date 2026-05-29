"""
Property-based tests for rate limiter enforcement.

Feature: ipl-live-score-integration
Property 21: Rate limiter enforcement
Validates: Requirements 7.3
"""

import asyncio
import pytest
from hypothesis import given, settings, strategies as st
from rate_limiter import RateLimiter


class FakeClock:
    """Deterministic async clock for rate limiter timing properties."""

    def __init__(self):
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.now += delay
        await asyncio.sleep(0)


# Feature: ipl-live-score-integration, Property 21: Rate limiter enforcement
@given(
    max_requests=st.integers(min_value=1, max_value=10),
    time_window=st.integers(min_value=1, max_value=10),
    num_requests=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=20, deadline=5000)
@pytest.mark.asyncio
async def test_rate_limiter_enforcement(max_requests, time_window, num_requests):
    """
    **Validates: Requirements 7.3**
    
    Property: For any sequence of API requests to the Score_Provider within
    a time window, no more than max_requests should be allowed through.
    
    This test verifies that the rate limiter correctly enforces the configured
    rate limit by attempting to make more requests than allowed and ensuring
    that only the permitted number succeed immediately.
    """
    # Create and configure rate limiter
    clock = FakeClock()
    limiter = RateLimiter(sleep=clock.sleep, clock=clock.monotonic)
    limiter.configure("test_endpoint", max_requests=max_requests, time_window=time_window)
    
    # Track successful requests
    successful_requests = 0
    
    # Attempt to make num_requests requests as fast as possible
    for _ in range(num_requests):
        if await limiter.acquire("test_endpoint"):
            successful_requests += 1
    
    # Property: No more than max_requests should succeed immediately
    assert successful_requests <= max_requests, (
        f"Rate limiter allowed {successful_requests} requests, "
        f"but should allow at most {max_requests}"
    )
    
    # Additional check: If we requested more than capacity, we should hit the limit
    if num_requests > max_requests:
        assert successful_requests == max_requests, (
            f"Rate limiter should allow exactly {max_requests} requests "
            f"when capacity is full, but allowed {successful_requests}"
        )


# Feature: ipl-live-score-integration, Property 21: Rate limiter enforcement
@given(
    max_requests=st.integers(min_value=2, max_value=6),
    time_window=st.floats(min_value=1.0, max_value=5.0)
)
@settings(max_examples=20, deadline=10000)
@pytest.mark.asyncio
async def test_rate_limiter_refill_over_time(max_requests, time_window):
    """
    **Validates: Requirements 7.3**
    
    Property: After consuming all tokens, waiting for the time window should
    allow new requests to be made (tokens refill over time).
    
    This test verifies that the token bucket refills correctly over time,
    allowing new requests after the rate limit has been reached.
    """
    # Create and configure rate limiter
    clock = FakeClock()
    limiter = RateLimiter(sleep=clock.sleep, clock=clock.monotonic)
    limiter.configure("test_endpoint", max_requests=max_requests, time_window=time_window)
    
    # Consume all tokens
    for _ in range(max_requests):
        acquired = await limiter.acquire("test_endpoint")
        assert acquired, "Should be able to acquire initial tokens"
    
    # Next request should fail (bucket is empty)
    acquired = await limiter.acquire("test_endpoint")
    assert not acquired, "Should not be able to acquire when bucket is empty"
    
    # Calculate expected refill time for one token
    refill_rate = max_requests / time_window
    time_for_one_token = 1.0 / refill_rate
    
    # Wait for slightly more than one token to refill
    await clock.sleep(time_for_one_token * 1.2)
    
    # Now we should be able to acquire at least one token
    acquired = await limiter.acquire("test_endpoint")
    assert acquired, (
        f"Should be able to acquire token after waiting {time_for_one_token * 1.2:.2f}s "
        f"(refill rate: {refill_rate:.2f} tokens/s)"
    )


# Feature: ipl-live-score-integration, Property 21: Rate limiter enforcement
@given(
    max_requests=st.integers(min_value=3, max_value=8),
    time_window=st.integers(min_value=2, max_value=6)
)
@settings(max_examples=20, deadline=5000)
@pytest.mark.asyncio
async def test_rate_limiter_wait_time_accuracy(max_requests, time_window):
    """
    **Validates: Requirements 7.3**
    
    Property: The wait time returned by get_wait_time should accurately
    reflect when the next token will be available.
    
    This test verifies that the get_wait_time method provides accurate
    information about when the next request can be made.
    """
    # Create and configure rate limiter
    clock = FakeClock()
    limiter = RateLimiter(sleep=clock.sleep, clock=clock.monotonic)
    limiter.configure("test_endpoint", max_requests=max_requests, time_window=time_window)
    
    # Consume all tokens
    for _ in range(max_requests):
        await limiter.acquire("test_endpoint")
    
    # Get wait time for next token
    wait_time = limiter.get_wait_time("test_endpoint")
    
    # Wait time should be positive (we need to wait)
    assert wait_time > 0, "Wait time should be positive when bucket is empty"
    
    # Calculate expected wait time
    refill_rate = max_requests / time_window
    expected_wait_time = 1.0 / refill_rate
    
    # Wait time should be approximately equal to time for one token
    # Allow 10% tolerance for timing precision
    tolerance = expected_wait_time * 0.1
    assert abs(wait_time - expected_wait_time) <= tolerance, (
        f"Wait time {wait_time:.3f}s should be close to expected "
        f"{expected_wait_time:.3f}s (tolerance: {tolerance:.3f}s)"
    )


# Feature: ipl-live-score-integration, Property 21: Rate limiter enforcement
@given(
    max_requests=st.integers(min_value=4, max_value=10),
    time_window=st.integers(min_value=2, max_value=8),
    partial_consume=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=20, deadline=5000)
@pytest.mark.asyncio
async def test_rate_limiter_partial_consumption(max_requests, time_window, partial_consume):
    """
    **Validates: Requirements 7.3**
    
    Property: After consuming some (but not all) tokens, the number of
    remaining available requests should be correct.
    
    This test verifies that the rate limiter correctly tracks partial
    token consumption.
    """
    # Ensure we don't try to consume more than available
    if partial_consume >= max_requests:
        partial_consume = max_requests - 1
    
    # Create and configure rate limiter
    clock = FakeClock()
    limiter = RateLimiter(sleep=clock.sleep, clock=clock.monotonic)
    limiter.configure("test_endpoint", max_requests=max_requests, time_window=time_window)
    
    # Consume some tokens
    for _ in range(partial_consume):
        acquired = await limiter.acquire("test_endpoint")
        assert acquired, f"Should be able to acquire token {_ + 1}/{partial_consume}"
    
    # Check available tokens
    available = limiter.get_available_tokens("test_endpoint")
    expected_available = max_requests - partial_consume
    
    # Available tokens should match expected (allow small floating point error)
    assert abs(available - expected_available) < 0.01, (
        f"After consuming {partial_consume} tokens, should have "
        f"{expected_available} available, but have {available:.2f}"
    )
    
    # Should be able to acquire remaining tokens
    remaining_acquired = 0
    for _ in range(max_requests):  # Try more than remaining to test limit
        if await limiter.acquire("test_endpoint"):
            remaining_acquired += 1
    
    # Should have acquired exactly the remaining tokens
    assert remaining_acquired == expected_available, (
        f"Should be able to acquire {expected_available} more tokens, "
        f"but acquired {remaining_acquired}"
    )


# Feature: ipl-live-score-integration, Property 21: Rate limiter enforcement
@pytest.mark.asyncio
async def test_rate_limiter_cricbuzz_configuration():
    """
    **Validates: Requirements 7.3**
    
    Property: The rate limiter configured for Cricbuzz API (6 requests per minute)
    should enforce exactly that limit.
    
    This test verifies the specific Cricbuzz API rate limit requirement.
    """
    # Create and configure rate limiter for Cricbuzz (6 requests per 60 seconds)
    clock = FakeClock()
    limiter = RateLimiter(sleep=clock.sleep, clock=clock.monotonic)
    limiter.configure("cricbuzz_api", max_requests=6, time_window=60)
    
    # Attempt to make 10 requests rapidly
    successful_requests = 0
    for _ in range(10):
        if await limiter.acquire("cricbuzz_api"):
            successful_requests += 1
    
    # Should allow exactly 6 requests
    assert successful_requests == 6, (
        f"Cricbuzz rate limiter should allow exactly 6 requests per minute, "
        f"but allowed {successful_requests}"
    )
    
    # Check that wait time is reasonable (should be ~10 seconds for next token)
    wait_time = limiter.get_wait_time("cricbuzz_api")
    expected_wait = 60.0 / 6.0  # 10 seconds per token
    
    # Allow 10% tolerance
    tolerance = expected_wait * 0.1
    assert abs(wait_time - expected_wait) <= tolerance, (
        f"Wait time {wait_time:.2f}s should be close to {expected_wait:.2f}s "
        f"for Cricbuzz rate limit"
    )
