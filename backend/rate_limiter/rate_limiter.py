"""
Rate limiter implementation using token bucket algorithm.

This module provides rate limiting functionality to control the frequency
of API requests to external services like Cricbuzz.
"""

import asyncio
import time
from typing import Awaitable, Callable, Dict
from dataclasses import dataclass, field


TOKEN_EPSILON = 1e-9


@dataclass
class TokenBucket:
    """Token bucket for rate limiting a specific endpoint."""
    
    capacity: int  # Maximum number of tokens (requests)
    refill_rate: float  # Tokens added per second
    clock: Callable[[], float] = time.monotonic
    tokens: float = field(init=False)  # Current available tokens
    last_refill: float = field(init=False)  # Last refill timestamp
    
    def __post_init__(self):
        """Initialize tokens to full capacity."""
        self.tokens = float(self.capacity)
        self.last_refill = self.clock()
    
    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = self.clock()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time and refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self.refill()
        
        if self.tokens + TOKEN_EPSILON >= tokens:
            self.tokens = max(0.0, self.tokens - tokens)
            return True
        return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Calculate time to wait until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed (default: 1)
            
        Returns:
            Time in seconds to wait, or 0 if tokens are available now
        """
        self.refill()
        
        if self.tokens + TOKEN_EPSILON >= tokens:
            return 0.0
        
        # Calculate how many tokens we need
        tokens_needed = tokens - self.tokens
        
        # Calculate time to accumulate needed tokens
        wait_time = tokens_needed / self.refill_rate
        return wait_time


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    
    Supports configurable rate limits per endpoint and request queuing
    when rate limits are reached.
    
    Example:
        limiter = RateLimiter()
        limiter.configure("cricbuzz_api", max_requests=6, time_window=60)
        
        if await limiter.acquire("cricbuzz_api"):
            # Make API request
            pass
        else:
            # Rate limit reached, wait or queue
            wait_time = limiter.get_wait_time("cricbuzz_api")
    """
    
    def __init__(
        self,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        """Initialize rate limiter with empty buckets."""
        self._buckets: Dict[str, TokenBucket] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._queue_tasks: Dict[str, asyncio.Task] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._sleep = sleep
        self._clock = clock
    
    def configure(
        self,
        key: str,
        max_requests: int,
        time_window: float
    ) -> None:
        """
        Configure rate limit for a specific endpoint.
        
        Args:
            key: Identifier for the endpoint (e.g., "cricbuzz_api")
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
            
        Example:
            # Allow 6 requests per 60 seconds (1 minute)
            limiter.configure("cricbuzz_api", max_requests=6, time_window=60)
        """
        if max_requests <= 0:
            raise ValueError("max_requests must be greater than zero")
        if time_window <= 0:
            raise ValueError("time_window must be greater than zero")

        # Calculate refill rate (tokens per second)
        refill_rate = max_requests / time_window
        
        # Create token bucket with capacity equal to max_requests
        self._buckets[key] = TokenBucket(
            capacity=max_requests,
            refill_rate=refill_rate,
            clock=self._clock,
        )
        
        # Initialize queue for this endpoint
        self._queues[key] = asyncio.Queue()
        self._locks[key] = asyncio.Lock()

    def _get_bucket(self, key: str) -> TokenBucket:
        if key not in self._buckets:
            raise KeyError(f"Rate limiter not configured for key: {key}")
        return self._buckets[key]
    
    async def acquire(self, key: str) -> bool:
        """
        Attempt to acquire rate limit token.
        
        Args:
            key: Identifier for the endpoint
            
        Returns:
            True if token was acquired, False if rate limit reached
            
        Raises:
            KeyError: If the key has not been configured
        """
        bucket = self._get_bucket(key)
        async with self._locks[key]:
            return bucket.consume()
    
    def get_wait_time(self, key: str) -> float:
        """
        Get time until next available slot.
        
        Args:
            key: Identifier for the endpoint
            
        Returns:
            Time in seconds to wait, or 0 if slot is available now
            
        Raises:
            KeyError: If the key has not been configured
        """
        bucket = self._get_bucket(key)
        return bucket.get_wait_time()
    
    async def queue_request(self, key: str) -> None:
        """
        Queue a request to be executed when rate limit allows.
        
        This method will block until a token becomes available.
        
        Args:
            key: Identifier for the endpoint
            
        Raises:
            KeyError: If the key has not been configured
        """
        bucket = self._get_bucket(key)
        async with self._locks[key]:
            # Holding the per-key lock while waiting gives concurrent callers
            # FIFO-style queuing instead of letting all waiters wake and race.
            while not bucket.consume():
                wait_time = bucket.get_wait_time()
                await self._sleep(wait_time)
    
    async def execute_with_limit(self, key: str, coro):
        """
        Execute a coroutine with rate limiting.
        
        This method will automatically queue the request if rate limit
        is reached and execute it when a slot becomes available.
        
        Args:
            key: Identifier for the endpoint
            coro: Coroutine to execute
            
        Returns:
            Result of the coroutine execution
            
        Raises:
            KeyError: If the key has not been configured
        """
        await self.queue_request(key)
        return await coro
    
    def reset(self, key: str) -> None:
        """
        Reset rate limiter for a specific endpoint.
        
        Args:
            key: Identifier for the endpoint
            
        Raises:
            KeyError: If the key has not been configured
        """
        bucket = self._get_bucket(key)
        # Reset bucket to full capacity
        bucket.tokens = float(bucket.capacity)
        bucket.last_refill = self._clock()
    
    def get_available_tokens(self, key: str) -> float:
        """
        Get number of currently available tokens.
        
        Args:
            key: Identifier for the endpoint
            
        Returns:
            Number of available tokens (may be fractional)
            
        Raises:
            KeyError: If the key has not been configured
        """
        bucket = self._get_bucket(key)
        bucket.refill()
        return bucket.tokens
