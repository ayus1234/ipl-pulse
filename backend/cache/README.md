# Cache Module

This module provides a flexible caching layer for the IPL Live Score Integration platform. It supports both in-memory caching for development and Redis caching for production deployments.

## Features

- **Abstract Interface**: `CacheService` defines a consistent interface for all cache implementations
- **In-Memory Cache**: Fast, local caching suitable for development and single-instance deployments
- **Redis Cache**: Distributed caching for production multi-instance deployments
- **TTL Support**: Automatic expiration of cached data based on configurable time-to-live values
- **Factory Pattern**: Easy instantiation based on environment configuration
- **Cache Key Utilities**: Standardized key generation for consistent caching patterns

## Quick Start

### Basic Usage

```python
from backend.cache import create_cache, CacheTTL, generate_cache_key

# Create a cache instance (defaults to in-memory)
cache = create_cache()

# For async applications, start the cache
await cache.start()  # Only needed for MemoryCache

# Store a value with TTL
key = generate_cache_key("match", "12345", "details")
await cache.set(key, match_data, ttl=CacheTTL.LIVE_DATA)

# Retrieve a value
data = await cache.get(key)

# Check if a key exists
exists = await cache.exists(key)

# Delete a value
await cache.delete(key)

# Clean up
await cache.stop()  # Only needed for MemoryCache
```

### Using Redis Cache

```python
from backend.cache import create_cache

# Create Redis cache with environment variables
# Set CACHE_TYPE=redis in your environment
cache = create_cache()

# Or create explicitly with custom configuration
cache = create_cache(
    "redis",
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    redis_password="your-password"
)

# Connect to Redis
await cache.connect()

# Use the cache
await cache.set("key", "value", ttl=60)
data = await cache.get("key")

# Disconnect when done
await cache.disconnect()
```

## Configuration

### Environment Variables

The cache module can be configured using environment variables:

- `CACHE_TYPE`: Type of cache to use (`memory` or `redis`). Default: `memory`
- `REDIS_HOST`: Redis server hostname. Default: `localhost`
- `REDIS_PORT`: Redis server port. Default: `6379`
- `REDIS_DB`: Redis database number. Default: `0`
- `REDIS_PASSWORD`: Redis password (optional)

### TTL Values

Standard TTL values are defined in `CacheTTL`:

- `LIVE_DATA`: 10 seconds - For live match data that changes frequently
- `SCHEDULE`: 60 seconds - For match schedules
- `HISTORICAL`: 300 seconds (5 minutes) - For historical match data
- `STATISTICS`: 300 seconds (5 minutes) - For aggregated statistics

## Cache Key Generation

Use `generate_cache_key()` to create standardized cache keys:

```python
from backend.cache import generate_cache_key

# Full key with all parts
key = generate_cache_key("match", "12345", "details")
# Result: "match:12345:details"

# Key without suffix
key = generate_cache_key("match", "12345")
# Result: "match:12345"

# Key without resource ID
key = generate_cache_key("matches", suffix="live")
# Result: "matches:live"

# Key with only resource type
key = generate_cache_key("schedule")
# Result: "schedule"
```

## Implementation Details

### MemoryCache

- Uses Python dictionary for storage
- Thread-safe for asyncio applications using `asyncio.Lock`
- Background cleanup task removes expired entries periodically
- Suitable for development and single-instance deployments
- No external dependencies

### RedisCache

- Uses `redis.asyncio` for async Redis operations
- Values are JSON-serialized for storage
- Leverages Redis TTL for automatic expiration
- Suitable for production multi-instance deployments
- Requires `redis` package: `pip install redis`

## Testing

The module includes comprehensive unit tests:

```bash
# Run all cache tests
pytest backend/tests/ -k "cache" -v

# Run specific test files
pytest backend/tests/test_cache_memory.py -v
pytest backend/tests/test_cache_utils.py -v
pytest backend/tests/test_cache_factory.py -v
```

Note: Redis tests are automatically skipped if the `redis` package is not installed.

## Integration Example

Here's how to integrate the cache with a service:

```python
from backend.cache import create_cache, CacheTTL, generate_cache_key

class LiveMatchService:
    def __init__(self):
        self.cache = create_cache()
    
    async def start(self):
        """Start the service and cache."""
        if hasattr(self.cache, 'start'):
            await self.cache.start()
        elif hasattr(self.cache, 'connect'):
            await self.cache.connect()
    
    async def stop(self):
        """Stop the service and cache."""
        if hasattr(self.cache, 'stop'):
            await self.cache.stop()
        elif hasattr(self.cache, 'disconnect'):
            await self.cache.disconnect()
    
    async def get_match_details(self, match_id: str):
        """Get match details with caching."""
        # Generate cache key
        cache_key = generate_cache_key("match", match_id, "details")
        
        # Check cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Fetch from API if not cached
        data = await self._fetch_from_api(match_id)
        
        # Store in cache
        await self.cache.set(cache_key, data, ttl=CacheTTL.LIVE_DATA)
        
        return data
    
    async def _fetch_from_api(self, match_id: str):
        # Implementation to fetch from external API
        pass
```

## Best Practices

1. **Use appropriate TTL values**: Choose TTL based on data freshness requirements
2. **Generate consistent keys**: Use `generate_cache_key()` for standardized keys
3. **Handle cache misses gracefully**: Always have a fallback when cache returns None
4. **Clean up resources**: Call `stop()` or `disconnect()` when shutting down
5. **Use Redis for production**: In-memory cache doesn't scale across multiple instances
6. **Monitor cache hit rates**: Track cache effectiveness in production

## Requirements

- Python 3.8+
- `redis` package (optional, only for RedisCache)

## License

Part of the IPL Live Score Integration project.
