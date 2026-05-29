"""
Unit tests for cache factory.

These tests verify that the factory creates the correct cache type
based on configuration.
"""

import pytest
import os
from backend.cache import create_cache, MemoryCache, RedisCache

# Check if redis is available
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


def test_create_memory_cache_explicit():
    """Test creating memory cache with explicit type."""
    cache = create_cache("memory")
    assert isinstance(cache, MemoryCache)


def test_create_memory_cache_default():
    """Test that memory cache is created by default."""
    # Clear environment variable if set
    old_value = os.environ.pop("CACHE_TYPE", None)
    
    try:
        cache = create_cache()
        assert isinstance(cache, MemoryCache)
    finally:
        # Restore environment variable
        if old_value:
            os.environ["CACHE_TYPE"] = old_value


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_create_redis_cache_explicit():
    """Test creating Redis cache with explicit type."""
    cache = create_cache("redis")
    assert isinstance(cache, RedisCache)


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_create_redis_cache_with_custom_config():
    """Test creating Redis cache with custom configuration."""
    cache = create_cache(
        "redis",
        redis_host="custom-host",
        redis_port=6380,
        redis_db=1,
        redis_password="secret"
    )
    assert isinstance(cache, RedisCache)
    assert cache._host == "custom-host"
    assert cache._port == 6380
    assert cache._db == 1
    assert cache._password == "secret"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_create_cache_from_env():
    """Test creating cache based on environment variable."""
    old_value = os.environ.get("CACHE_TYPE")
    
    try:
        # Test memory cache from env
        os.environ["CACHE_TYPE"] = "memory"
        cache = create_cache()
        assert isinstance(cache, MemoryCache)
        
        # Test redis cache from env
        os.environ["CACHE_TYPE"] = "redis"
        cache = create_cache()
        assert isinstance(cache, RedisCache)
    finally:
        # Restore environment variable
        if old_value:
            os.environ["CACHE_TYPE"] = old_value
        else:
            os.environ.pop("CACHE_TYPE", None)


def test_create_cache_invalid_type():
    """Test that invalid cache type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown cache type"):
        create_cache("invalid")


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_redis_config_from_env():
    """Test that Redis configuration is read from environment."""
    old_values = {
        "REDIS_HOST": os.environ.get("REDIS_HOST"),
        "REDIS_PORT": os.environ.get("REDIS_PORT"),
        "REDIS_DB": os.environ.get("REDIS_DB"),
        "REDIS_PASSWORD": os.environ.get("REDIS_PASSWORD"),
    }
    
    try:
        os.environ["REDIS_HOST"] = "env-host"
        os.environ["REDIS_PORT"] = "6380"
        os.environ["REDIS_DB"] = "2"
        os.environ["REDIS_PASSWORD"] = "env-secret"
        
        cache = create_cache("redis")
        assert isinstance(cache, RedisCache)
        assert cache._host == "env-host"
        assert cache._port == 6380
        assert cache._db == 2
        assert cache._password == "env-secret"
    finally:
        # Restore environment variables
        for key, value in old_values.items():
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
def test_redis_config_parameter_overrides_env():
    """Test that explicit parameters override environment variables."""
    old_host = os.environ.get("REDIS_HOST")
    
    try:
        os.environ["REDIS_HOST"] = "env-host"
        
        cache = create_cache("redis", redis_host="param-host")
        assert isinstance(cache, RedisCache)
        assert cache._host == "param-host"
    finally:
        if old_host:
            os.environ["REDIS_HOST"] = old_host
        else:
            os.environ.pop("REDIS_HOST", None)
