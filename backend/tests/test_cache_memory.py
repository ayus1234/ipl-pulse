"""
Unit tests for MemoryCache implementation.

These tests verify the in-memory cache behavior including TTL,
expiration, and basic operations.
"""

import pytest
import pytest_asyncio
import asyncio
from backend.cache import MemoryCache


@pytest_asyncio.fixture
async def cache():
    """Create a MemoryCache instance for testing."""
    cache = MemoryCache(cleanup_interval=1)
    await cache.start()
    yield cache
    await cache.stop()


@pytest.mark.asyncio
async def test_set_and_get(cache):
    """Test basic set and get operations."""
    await cache.set("key1", "value1", ttl=10)
    result = await cache.get("key1")
    assert result == "value1"


@pytest.mark.asyncio
async def test_get_nonexistent_key(cache):
    """Test getting a key that doesn't exist."""
    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_ttl_expiration(cache):
    """Test that values expire after TTL."""
    await cache.set("key1", "value1", ttl=1)
    
    # Should exist immediately
    result = await cache.get("key1")
    assert result == "value1"
    
    # Wait for expiration
    await asyncio.sleep(1.1)
    
    # Should be expired
    result = await cache.get("key1")
    assert result is None


@pytest.mark.asyncio
async def test_delete(cache):
    """Test deleting a key."""
    await cache.set("key1", "value1", ttl=10)
    await cache.delete("key1")
    
    result = await cache.get("key1")
    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_key(cache):
    """Test deleting a key that doesn't exist (should not raise error)."""
    await cache.delete("nonexistent")
    # Should complete without error


@pytest.mark.asyncio
async def test_exists(cache):
    """Test checking if a key exists."""
    await cache.set("key1", "value1", ttl=10)
    
    assert await cache.exists("key1") is True
    assert await cache.exists("nonexistent") is False


@pytest.mark.asyncio
async def test_exists_expired_key(cache):
    """Test that exists returns False for expired keys."""
    await cache.set("key1", "value1", ttl=1)
    
    # Should exist immediately
    assert await cache.exists("key1") is True
    
    # Wait for expiration
    await asyncio.sleep(1.1)
    
    # Should not exist after expiration
    assert await cache.exists("key1") is False


@pytest.mark.asyncio
async def test_overwrite_value(cache):
    """Test overwriting an existing key."""
    await cache.set("key1", "value1", ttl=10)
    await cache.set("key1", "value2", ttl=10)
    
    result = await cache.get("key1")
    assert result == "value2"


@pytest.mark.asyncio
async def test_multiple_keys(cache):
    """Test storing multiple keys."""
    await cache.set("key1", "value1", ttl=10)
    await cache.set("key2", "value2", ttl=10)
    await cache.set("key3", "value3", ttl=10)
    
    assert await cache.get("key1") == "value1"
    assert await cache.get("key2") == "value2"
    assert await cache.get("key3") == "value3"


@pytest.mark.asyncio
async def test_clear(cache):
    """Test clearing all cache entries."""
    await cache.set("key1", "value1", ttl=10)
    await cache.set("key2", "value2", ttl=10)
    
    await cache.clear()
    
    assert await cache.get("key1") is None
    assert await cache.get("key2") is None


@pytest.mark.asyncio
async def test_complex_values(cache):
    """Test caching complex data structures."""
    complex_value = {
        "list": [1, 2, 3],
        "dict": {"nested": "value"},
        "number": 42,
        "string": "test"
    }
    
    await cache.set("complex", complex_value, ttl=10)
    result = await cache.get("complex")
    
    assert result == complex_value


@pytest.mark.asyncio
async def test_background_cleanup(cache):
    """Test that background cleanup removes expired entries."""
    # Set multiple keys with short TTL
    await cache.set("key1", "value1", ttl=1)
    await cache.set("key2", "value2", ttl=1)
    await cache.set("key3", "value3", ttl=1)
    
    # Verify they exist
    assert cache.size() == 3
    
    # Wait for expiration and cleanup
    await asyncio.sleep(2)
    
    # Size should be 0 after cleanup
    assert cache.size() == 0


@pytest.mark.asyncio
async def test_different_ttls(cache):
    """Test keys with different TTL values."""
    await cache.set("short", "value1", ttl=1)
    await cache.set("long", "value2", ttl=10)
    
    # Wait for short TTL to expire
    await asyncio.sleep(1.1)
    
    # Short should be expired, long should still exist
    assert await cache.get("short") is None
    assert await cache.get("long") == "value2"
