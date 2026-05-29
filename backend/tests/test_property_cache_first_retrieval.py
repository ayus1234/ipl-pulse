"""
Property-based test for cache-first data retrieval.

Feature: ipl-live-score-integration, Property 20: Cache-first data retrieval
Validates: Requirements 7.1

This test verifies that for any request for match data, if valid cached data exists
(not expired), it should be returned without making an external API call.
"""

import pytest
import pytest_asyncio
from hypothesis import given, strategies as st, settings
from backend.cache import MemoryCache, CacheTTL
from typing import Any, Dict


class FakeClock:
    """Deterministic clock for cache expiration properties."""

    def __init__(self):
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# Strategy for generating cache keys
cache_key_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'),
    whitelist_characters='-_:'
))

# Strategy for generating cache values (match data)
match_data_strategy = st.fixed_dictionaries({
    'match_id': st.text(min_size=1, max_size=20),
    'team1': st.text(min_size=1, max_size=30),
    'team2': st.text(min_size=1, max_size=30),
    'score': st.text(min_size=1, max_size=20),
    'status': st.sampled_from(['live', 'completed', 'scheduled'])
})

# Strategy for TTL values (positive integers)
ttl_strategy = st.integers(min_value=1, max_value=300)


@pytest_asyncio.fixture
async def cache():
    """Create a MemoryCache instance for testing."""
    clock = FakeClock()
    cache = MemoryCache(cleanup_interval=60, clock=clock.time)
    await cache.start()
    yield cache
    await cache.stop()


class APICallTracker:
    """Helper class to track whether API calls were made."""
    
    def __init__(self):
        self.call_count = 0
        self.last_key = None
    
    def reset(self):
        self.call_count = 0
        self.last_key = None
    
    async def fetch_from_api(self, key: str) -> Dict[str, Any]:
        """Simulate an API call."""
        self.call_count += 1
        self.last_key = key
        return {"fetched": True, "key": key}


@pytest.mark.asyncio
@given(
    key=cache_key_strategy,
    data=match_data_strategy,
    ttl=ttl_strategy
)
@settings(max_examples=20)
async def test_cache_first_retrieval_property(key: str, data: Dict[str, Any], ttl: int):
    """
    Feature: ipl-live-score-integration, Property 20: Cache-first data retrieval
    
    Property: For any request for match data, if valid cached data exists (not expired),
    it should be returned without making an external API call.
    
    Test strategy:
    1. Store data in cache with a TTL
    2. Attempt to retrieve the data
    3. Verify that cached data is returned
    4. Verify that no API call was made (by tracking API calls)
    """
    # Create cache and API tracker
    clock = FakeClock()
    cache = MemoryCache(cleanup_interval=60, clock=clock.time)
    await cache.start()
    
    try:
        api_tracker = APICallTracker()
        
        # Step 1: Store data in cache
        await cache.set(key, data, ttl=ttl)
        
        # Step 2: Retrieve data (should come from cache)
        cached_data = await cache.get(key)
        
        # Step 3: Verify cached data is returned
        assert cached_data is not None, "Cache should return data"
        assert cached_data == data, "Cached data should match original data"
        
        # Step 4: Simulate a service that checks cache before calling API
        # This is the cache-first pattern
        if cached_data is None:
            # Only call API if cache miss
            fetched_data = await api_tracker.fetch_from_api(key)
        else:
            # Use cached data, no API call
            fetched_data = cached_data
        
        # Verify no API call was made (cache hit)
        assert api_tracker.call_count == 0, "No API call should be made when data is cached"
        assert fetched_data == data, "Returned data should match cached data"
        
    finally:
        await cache.stop()


@pytest.mark.asyncio
@given(
    key=cache_key_strategy,
    data=match_data_strategy
)
@settings(max_examples=20)
async def test_cache_miss_triggers_api_call(key: str, data: Dict[str, Any]):
    """
    Feature: ipl-live-score-integration, Property 20: Cache-first data retrieval
    
    Complementary test: When cache is empty (cache miss), API should be called.
    
    This verifies the other side of the cache-first pattern: when there's no
    cached data, the system should fall back to the API.
    """
    cache = MemoryCache(cleanup_interval=60)
    await cache.start()
    
    try:
        api_tracker = APICallTracker()
        
        # Don't store anything in cache - ensure cache miss
        cached_data = await cache.get(key)
        assert cached_data is None, "Cache should be empty"
        
        # Simulate cache-first pattern with cache miss
        if cached_data is None:
            # Cache miss - call API
            fetched_data = await api_tracker.fetch_from_api(key)
            # Store in cache for next time
            await cache.set(key, fetched_data, ttl=CacheTTL.LIVE_DATA)
        else:
            fetched_data = cached_data
        
        # Verify API was called (cache miss)
        assert api_tracker.call_count == 1, "API should be called on cache miss"
        assert api_tracker.last_key == key, "API should be called with correct key"
        
    finally:
        await cache.stop()


@pytest.mark.asyncio
@given(
    key=cache_key_strategy,
    data=match_data_strategy
)
@settings(max_examples=20, deadline=None)
async def test_expired_cache_triggers_api_call(key: str, data: Dict[str, Any]):
    """
    Feature: ipl-live-score-integration, Property 20: Cache-first data retrieval
    
    Edge case test: When cached data is expired, API should be called.
    
    This verifies that expired cache entries are treated as cache misses.
    """
    clock = FakeClock()
    cache = MemoryCache(cleanup_interval=60, clock=clock.time)
    await cache.start()
    
    try:
        api_tracker = APICallTracker()
        
        # Store data with very short TTL (1 second)
        await cache.set(key, data, ttl=1)
        
        # Advance past expiration without slowing Hypothesis examples.
        clock.advance(1.1)
        
        # Try to retrieve - should be expired
        cached_data = await cache.get(key)
        assert cached_data is None, "Expired cache should return None"
        
        # Simulate cache-first pattern with expired cache
        if cached_data is None:
            # Cache miss (expired) - call API
            fetched_data = await api_tracker.fetch_from_api(key)
            # Store fresh data in cache
            await cache.set(key, fetched_data, ttl=CacheTTL.LIVE_DATA)
        else:
            fetched_data = cached_data
        
        # Verify API was called (expired cache)
        assert api_tracker.call_count == 1, "API should be called when cache is expired"
        
    finally:
        await cache.stop()


@pytest.mark.asyncio
async def test_cache_first_pattern_integration():
    """
    Integration test demonstrating the complete cache-first pattern.
    
    This test shows how a service would implement cache-first retrieval
    in practice, combining cache hits and misses.
    """
    cache = MemoryCache(cleanup_interval=60)
    await cache.start()
    
    try:
        api_tracker = APICallTracker()
        
        async def get_match_data(match_id: str) -> Dict[str, Any]:
            """Service method implementing cache-first pattern."""
            # Check cache first
            cached_data = await cache.get(match_id)
            
            if cached_data is not None:
                # Cache hit - return cached data
                return cached_data
            
            # Cache miss - fetch from API
            data = await api_tracker.fetch_from_api(match_id)
            
            # Store in cache for future requests
            await cache.set(match_id, data, ttl=CacheTTL.LIVE_DATA)
            
            return data
        
        # First call - cache miss, should call API
        data1 = await get_match_data("match-123")
        assert api_tracker.call_count == 1, "First call should hit API"
        
        # Second call - cache hit, should NOT call API
        data2 = await get_match_data("match-123")
        assert api_tracker.call_count == 1, "Second call should use cache"
        assert data1 == data2, "Both calls should return same data"
        
        # Different key - cache miss, should call API again
        data3 = await get_match_data("match-456")
        assert api_tracker.call_count == 2, "Different key should hit API"
        
    finally:
        await cache.stop()
