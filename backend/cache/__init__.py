"""
Cache module for IPL Live Score Integration.

This module provides caching functionality with support for both in-memory
and Redis backends.
"""

from .service import CacheService
from .memory_cache import MemoryCache
from .redis_cache import RedisCache
from .utils import generate_cache_key, CacheTTL
from .factory import create_cache

__all__ = [
    "CacheService",
    "MemoryCache",
    "RedisCache",
    "generate_cache_key",
    "CacheTTL",
    "create_cache",
]
