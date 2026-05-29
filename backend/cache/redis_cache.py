"""
Redis cache implementation for production deployments.

This implementation uses Redis as a distributed cache, suitable for
multi-instance deployments and high-performance scenarios.
"""

import json
from typing import Any, Optional
from .service import CacheService

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCache(CacheService):
    """
    Redis-based cache implementation.
    
    This cache uses Redis for distributed caching across multiple
    application instances. Requires the redis package to be installed.
    
    Values are serialized to JSON for storage.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        """
        Initialize the Redis cache.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Optional Redis password
            decode_responses: Whether to decode responses as strings
            
        Raises:
            ImportError: If redis package is not installed
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for RedisCache. "
                "Install it with: pip install redis"
            )
        
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._decode_responses = decode_responses
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """
        Establish connection to Redis server.
        
        This should be called when the application starts.
        """
        self._redis = await aioredis.from_url(
            f"redis://{self._host}:{self._port}/{self._db}",
            password=self._password,
            decode_responses=self._decode_responses
        )

    async def disconnect(self) -> None:
        """
        Close connection to Redis server.
        
        This should be called when the application shuts down.
        """
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _ensure_connected(self) -> None:
        """
        Ensure Redis connection is established.
        
        Raises:
            RuntimeError: If not connected to Redis
        """
        if self._redis is None:
            raise RuntimeError(
                "Redis connection not established. Call connect() first."
            )

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cached value if it exists and hasn't expired, None otherwise
        """
        self._ensure_connected()
        
        value = await self._redis.get(key)
        
        if value is None:
            return None
        
        # Deserialize from JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # If not JSON, return as-is
            return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store a value in the cache with a time-to-live.
        
        Args:
            key: The cache key to store under
            value: The value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds
        """
        self._ensure_connected()
        
        # Serialize to JSON
        try:
            serialized_value = json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Value must be JSON-serializable: {e}")
        
        await self._redis.setex(key, ttl, serialized_value)

    async def delete(self, key: str) -> None:
        """
        Remove a value from the cache.
        
        Args:
            key: The cache key to delete
        """
        self._ensure_connected()
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache and hasn't expired.
        
        Args:
            key: The cache key to check
            
        Returns:
            True if the key exists and hasn't expired, False otherwise
        """
        self._ensure_connected()
        result = await self._redis.exists(key)
        return result > 0

    async def clear(self) -> None:
        """
        Clear all entries from the cache.
        
        WARNING: This flushes the entire Redis database.
        Use with caution in production.
        """
        self._ensure_connected()
        await self._redis.flushdb()

    async def ping(self) -> bool:
        """
        Check if Redis connection is alive.
        
        Returns:
            True if connection is alive, False otherwise
        """
        try:
            self._ensure_connected()
            await self._redis.ping()
            return True
        except Exception:
            return False
