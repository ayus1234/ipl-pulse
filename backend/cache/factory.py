"""
Cache factory for creating cache instances based on configuration.

This module provides a factory function to instantiate the appropriate
cache implementation based on environment configuration.
"""

import os
from typing import Optional
from .service import CacheService
from .memory_cache import MemoryCache
from .redis_cache import RedisCache


def create_cache(
    cache_type: Optional[str] = None,
    redis_host: Optional[str] = None,
    redis_port: Optional[int] = None,
    redis_db: Optional[int] = None,
    redis_password: Optional[str] = None
) -> CacheService:
    """
    Create a cache instance based on configuration.
    
    The cache type can be specified explicitly or determined from
    environment variables. Defaults to in-memory cache for development.
    
    Args:
        cache_type: Type of cache ("memory" or "redis"). If None, reads from
                   CACHE_TYPE environment variable, defaulting to "memory"
        redis_host: Redis server hostname (defaults to REDIS_HOST env var or "localhost")
        redis_port: Redis server port (defaults to REDIS_PORT env var or 6379)
        redis_db: Redis database number (defaults to REDIS_DB env var or 0)
        redis_password: Redis password (defaults to REDIS_PASSWORD env var)
        
    Returns:
        A CacheService instance (MemoryCache or RedisCache)
        
    Examples:
        >>> # Create in-memory cache
        >>> cache = create_cache("memory")
        
        >>> # Create Redis cache with defaults
        >>> cache = create_cache("redis")
        
        >>> # Create Redis cache with custom config
        >>> cache = create_cache("redis", redis_host="redis.example.com", redis_port=6380)
    """
    # Determine cache type
    if cache_type is None:
        cache_type = os.getenv("CACHE_TYPE", "memory").lower()
    
    if cache_type == "redis":
        # Get Redis configuration from parameters or environment
        host = redis_host or os.getenv("REDIS_HOST", "localhost")
        port = redis_port or int(os.getenv("REDIS_PORT", "6379"))
        db = redis_db if redis_db is not None else int(os.getenv("REDIS_DB", "0"))
        password = redis_password or os.getenv("REDIS_PASSWORD")
        
        return RedisCache(
            host=host,
            port=port,
            db=db,
            password=password
        )
    
    elif cache_type == "memory":
        return MemoryCache()
    
    else:
        raise ValueError(
            f"Unknown cache type: {cache_type}. "
            "Supported types: 'memory', 'redis'"
        )
