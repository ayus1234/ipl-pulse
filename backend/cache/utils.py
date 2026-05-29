"""
Cache utility functions and constants.

This module provides helper functions for cache key generation and
TTL configuration.
"""

from enum import IntEnum
from typing import Optional


class CacheTTL(IntEnum):
    """
    Standard TTL values for different types of cached data.
    
    These values are configured according to the design specification:
    - LIVE_DATA: 10 seconds for live match data
    - SCHEDULE: 60 seconds for match schedules
    - HISTORICAL: 300 seconds (5 minutes) for historical data
    - STATISTICS: 300 seconds (5 minutes) for aggregated statistics
    """
    LIVE_DATA = 10
    SCHEDULE = 60
    HISTORICAL = 300
    STATISTICS = 300


def generate_cache_key(
    resource_type: str,
    *parts: object,
    suffix: Optional[str] = None
) -> str:
    """
    Generate a standardized cache key.
    
    Cache keys follow the format: {resource_type}:{part}:{suffix}
    
    Args:
        resource_type: The type of resource (e.g., "match", "player", "team")
        parts: Optional identifiers or qualifiers for the specific resource
        suffix: Optional additional qualifier (e.g., "details", "stats")
        
    Returns:
        A formatted cache key string
        
    Examples:
        >>> generate_cache_key("match", "12345", "details")
        'match:12345:details'
        >>> generate_cache_key("stats", "top", "batsmen", 10)
        'stats:top:batsmen:10'
        >>> generate_cache_key("matches", suffix="live")
        'matches:live'
        >>> generate_cache_key("schedule")
        'schedule'
    """
    key_parts = [resource_type]
    
    for part in parts:
        if part is not None and part != "":
            key_parts.append(str(part))
    
    if suffix:
        key_parts.append(str(suffix))
    
    return ":".join(key_parts)
