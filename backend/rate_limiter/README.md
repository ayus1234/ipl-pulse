# Rate Limiter Module

This module provides rate limiting functionality using the token bucket algorithm to control the frequency of API requests to external services.

## Features

- **Token Bucket Algorithm**: Efficient rate limiting with smooth request distribution
- **Configurable Limits**: Support for different rate limits per endpoint
- **Request Queuing**: Automatic queuing when rate limit is reached
- **Wait Time Calculation**: Inform callers of next available slot
- **Async Support**: Full asyncio integration for non-blocking operations

## Usage

### Basic Usage

```python
from rate_limiter import RateLimiter

# Create rate limiter instance
limiter = RateLimiter()

# Configure for Cricbuzz API (6 requests per minute)
limiter.configure("cricbuzz_api", max_requests=6, time_window=60)

# Try to acquire a token
if await limiter.acquire("cricbuzz_api"):
    # Make API request
    response = await make_api_call()
else:
    # Rate limit reached
    wait_time = limiter.get_wait_time("cricbuzz_api")
    print(f"Rate limit reached. Wait {wait_time:.2f} seconds")
```

### Automatic Queuing

```python
# Automatically queue and execute when slot is available
result = await limiter.execute_with_limit(
    "cricbuzz_api",
    make_api_call()
)
```

### Manual Queuing

```python
# Wait for next available slot
await limiter.queue_request("cricbuzz_api")

# Now make the request
response = await make_api_call()
```

### Check Available Tokens

```python
# Get current number of available tokens
tokens = limiter.get_available_tokens("cricbuzz_api")
print(f"Available tokens: {tokens}")
```

## Configuration

The rate limiter uses a token bucket algorithm where:
- **Capacity**: Maximum number of tokens (equal to max_requests)
- **Refill Rate**: Tokens added per second (max_requests / time_window)

Example configurations:

```python
# 6 requests per minute (Cricbuzz API)
limiter.configure("cricbuzz_api", max_requests=6, time_window=60)

# 100 requests per hour
limiter.configure("other_api", max_requests=100, time_window=3600)

# 10 requests per second
limiter.configure("fast_api", max_requests=10, time_window=1)
```

## Token Bucket Algorithm

The token bucket algorithm works as follows:

1. **Initialization**: Bucket starts with full capacity of tokens
2. **Refill**: Tokens are added continuously at the configured rate
3. **Consumption**: Each request consumes one token
4. **Limit**: If no tokens available, request is denied or queued

Benefits:
- Allows burst traffic up to capacity
- Smooth distribution of requests over time
- Predictable wait times
- No need for sliding windows or complex tracking

## API Reference

### RateLimiter

#### `configure(key: str, max_requests: int, time_window: float) -> None`
Configure rate limit for a specific endpoint.

#### `async acquire(key: str) -> bool`
Attempt to acquire a rate limit token. Returns True if successful, False if rate limit reached.

#### `get_wait_time(key: str) -> float`
Get time in seconds until next available slot. Returns 0 if slot is available now.

#### `async queue_request(key: str) -> None`
Queue a request to be executed when rate limit allows. Blocks until token is available.

#### `async execute_with_limit(key: str, coro) -> Any`
Execute a coroutine with automatic rate limiting and queuing.

#### `reset(key: str) -> None`
Reset rate limiter for a specific endpoint to full capacity.

#### `get_available_tokens(key: str) -> float`
Get number of currently available tokens.

## Testing

The rate limiter includes comprehensive property-based tests:

- **Property 21**: Rate limiter enforcement - ensures no more than configured requests per time window
- **Property 23**: Request queuing - ensures requests are queued and executed when slots become available

Run tests:
```bash
pytest backend/tests/test_property_rate_limiter.py -v
```

## Requirements

Validates requirements:
- 7.3: Rate limiting (max 6 requests per minute to Cricbuzz)
- 7.5: Request queuing when rate limit is reached
