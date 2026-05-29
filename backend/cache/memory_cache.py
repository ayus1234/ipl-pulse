"""
In-memory cache implementation with TTL support.

This implementation is suitable for development and single-instance deployments.
For production with multiple instances, use RedisCache instead.
"""

import asyncio
import time
from typing import Any, Callable, Dict, Optional, Tuple
from .service import CacheService


class MemoryCache(CacheService):
    """
    In-memory cache implementation using a Python dictionary.
    
    This cache stores values in memory with TTL (time-to-live) support.
    Expired entries are cleaned up lazily on access and periodically
    via a background task.
    
    Thread-safe for asyncio applications.
    """

    def __init__(self, cleanup_interval: int = 60, clock: Callable[[], float] = time.time):
        """
        Initialize the in-memory cache.
        
        Args:
            cleanup_interval: Interval in seconds for periodic cleanup of expired entries
            clock: Time provider used for TTL checks. Defaults to wall-clock time.
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cleanup_interval = cleanup_interval
        self._clock = clock
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """
        Start the background cleanup task.
        
        This should be called when the application starts.
        """
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """
        Stop the background cleanup task.
        
        This should be called when the application shuts down.
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cached value if it exists and hasn't expired, None otherwise
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            
            # Check if expired
            if self._clock() > expiry:
                del self._cache[key]
                return None
            
            return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store a value in the cache with a time-to-live.
        
        Args:
            key: The cache key to store under
            value: The value to cache
            ttl: Time-to-live in seconds
        """
        expiry = self._clock() + ttl
        
        async with self._lock:
            self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        """
        Remove a value from the cache.
        
        Args:
            key: The cache key to delete
        """
        async with self._lock:
            self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache and hasn't expired.
        
        Args:
            key: The cache key to check
            
        Returns:
            True if the key exists and hasn't expired, False otherwise
        """
        async with self._lock:
            if key not in self._cache:
                return False
            
            _, expiry = self._cache[key]
            
            # Check if expired
            if self._clock() > expiry:
                del self._cache[key]
                return False
            
            return True

    async def _cleanup_loop(self) -> None:
        """
        Background task that periodically removes expired entries.
        """
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue cleanup loop
                print(f"Error in cache cleanup: {e}")

    async def _cleanup_expired(self) -> None:
        """
        Remove all expired entries from the cache.
        """
        current_time = self._clock()
        
        async with self._lock:
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if current_time > expiry
            ]
            
            for key in expired_keys:
                del self._cache[key]

    async def clear(self) -> None:
        """
        Clear all entries from the cache.
        
        This is useful for testing and maintenance.
        """
        async with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """
        Get the current number of entries in the cache.
        
        Returns:
            The number of cached entries (including expired ones)
        """
        return len(self._cache)
