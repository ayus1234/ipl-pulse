"""
Unit tests for cache utility functions.

These tests verify cache key generation and TTL constants.
"""

import pytest
from backend.cache import generate_cache_key, CacheTTL


def test_generate_cache_key_with_all_parts():
    """Test cache key generation with all parts."""
    key = generate_cache_key("match", "12345", "details")
    assert key == "match:12345:details"


def test_generate_cache_key_with_multiple_parts():
    """Test cache key generation with more than three parts."""
    key = generate_cache_key("stats", "top", "batsmen", 10)
    assert key == "stats:top:batsmen:10"


def test_generate_cache_key_with_parts_and_suffix():
    """Test suffix compatibility with variadic key parts."""
    key = generate_cache_key("match", "12345", suffix="details")
    assert key == "match:12345:details"


def test_generate_cache_key_without_suffix():
    """Test cache key generation without suffix."""
    key = generate_cache_key("match", "12345")
    assert key == "match:12345"


def test_generate_cache_key_without_id():
    """Test cache key generation without resource ID."""
    key = generate_cache_key("matches", suffix="live")
    assert key == "matches:live"


def test_generate_cache_key_only_type():
    """Test cache key generation with only resource type."""
    key = generate_cache_key("schedule")
    assert key == "schedule"


def test_cache_ttl_values():
    """Test that CacheTTL constants have correct values."""
    assert CacheTTL.LIVE_DATA == 10
    assert CacheTTL.SCHEDULE == 60
    assert CacheTTL.HISTORICAL == 300
    assert CacheTTL.STATISTICS == 300


def test_cache_key_with_special_characters():
    """Test cache key generation with special characters in IDs."""
    key = generate_cache_key("match", "ipl-2024-match-01", "commentary")
    assert key == "match:ipl-2024-match-01:commentary"


def test_cache_key_consistency():
    """Test that same inputs produce same keys."""
    key1 = generate_cache_key("player", "123", "stats")
    key2 = generate_cache_key("player", "123", "stats")
    assert key1 == key2


def test_cache_key_uniqueness():
    """Test that different inputs produce different keys."""
    key1 = generate_cache_key("match", "123", "details")
    key2 = generate_cache_key("match", "456", "details")
    key3 = generate_cache_key("match", "123", "commentary")
    
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3
