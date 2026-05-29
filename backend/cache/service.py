"""
CacheService interface definition.

This module defines the abstract interface that all cache implementations
must follow.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheService(ABC):
    """
    Abstract base class for cache implementations.
    
    All cache implementations (in-memory, Redis, etc.) must implement
    this interface to ensure consistent behavior across the application.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cached value if it exists and hasn't expired, None otherwise
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store a value in the cache with a time-to-live.
        
        Args:
            key: The cache key to store under
            value: The value to cache (must be serializable)
            ttl: Time-to-live in seconds
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Remove a value from the cache.
        
        Args:
            key: The cache key to delete
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache and hasn't expired.
        
        Args:
            key: The cache key to check
            
        Returns:
            True if the key exists and hasn't expired, False otherwise
        """
        pass
