"""Property tests for error handling and resilience."""

import pytest
import logging
from unittest.mock import patch, MagicMock
from fastapi import Request, HTTPException
from hypothesis import given, settings, strategies as st
from uuid import uuid4

from backend.middleware.error_handler import global_error_handler, ErrorFormatter
from backend.utils.logger import log_event
from backend.utils.resilience import OperationQueue
from backend.cache import MemoryCache


# Feature: ipl-live-score-integration, Property 22: Fallback to cache on failure
@pytest.mark.asyncio
async def test_fallback_to_cache_on_failure():
    """
    **Validates: Requirements 7.4, 9.5**
    """
    cache = MemoryCache()
    await cache.set("test_key", {"data": "cached_value"}, ttl=60)
    
    # Simulate an API or DB call that fails
    async def failing_call():
        raise Exception("Database timeout")
        
    async def resilient_fetch(key):
        try:
            return await failing_call()
        except Exception:
            # Fallback to cache
            return await cache.get(key)
            
    result = await resilient_fetch("test_key")
    assert result is not None
    assert result["data"] == "cached_value"


# Feature: ipl-live-score-integration, Property 26: Operation queuing during database outage
@pytest.mark.asyncio
async def test_operation_queuing_during_outage():
    """
    **Validates: Requirements 9.3**
    """
    queue = OperationQueue(max_size=5)
    
    # Simulate DB outage
    db_is_down = True
    
    mock_db = {}
    
    def save_to_db(k, v):
        if db_is_down:
            raise Exception("DB Down")
        mock_db[k] = v
        
    async def safe_save(k, v):
        try:
            save_to_db(k, v)
        except Exception:
            await queue.add("save_data", save_to_db, k, v)
            
    # Attempt to save while down
    await safe_save("k1", "v1")
    await safe_save("k2", "v2")
    
    assert len(mock_db) == 0
    assert len(queue.queue) == 2
    
    # DB comes back online
    db_is_down = False
    await queue.process_queue()
    
    assert len(queue.queue) == 0
    assert len(mock_db) == 2
    assert mock_db["k1"] == "v1"
    assert mock_db["k2"] == "v2"


# Feature: ipl-live-score-integration, Property 27: User-friendly error messages
@given(
    error_type=st.sampled_from(["rate_limit", "database_error", "api_timeout", "not_found", "validation_error", "auth_error", "unknown"]),
    detail=st.text(min_size=1, max_size=50)
)
@settings(max_examples=10, deadline=None)
def test_user_friendly_error_messages(error_type, detail):
    """
    **Validates: Requirements 9.4**
    """
    response = ErrorFormatter.format_error(error_type, detail)
    
    assert response["error"] is True
    assert response["type"] == error_type
    assert isinstance(response["message"], str)
    assert len(response["message"]) > 10 # Meaningful message
    assert response["detail"] == detail


# Feature: ipl-live-score-integration, Property 28: Comprehensive event logging
@patch("backend.utils.logger.logger")
def test_comprehensive_event_logging(mock_logger):
    """
    **Validates: Requirements 7.6, 9.6**
    """
    log_event(
        action="user_login",
        user="test_user",
        result="success",
        ip_address="127.0.0.1"
    )
    
    mock_logger.info.assert_called_once()
    args, kwargs = mock_logger.info.call_args
    assert "Event: user_login" in args[0]
    
    extra = kwargs.get("extra")
    assert extra is not None
    assert "context" in extra
    assert extra["context"]["action"] == "user_login"
    assert extra["context"]["user"] == "test_user"
    assert extra["context"]["result"] == "success"
    assert extra["context"]["ip_address"] == "127.0.0.1"
    
    # Test error logging
    mock_logger.reset_mock()
    log_event("db_query", result="error", query="SELECT *")
    mock_logger.error.assert_called_once()


# Unit tests for specific error scenarios
@pytest.mark.asyncio
async def test_global_error_handler():
    """Test global error handler middleware."""
    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/api/test"
    
    # Test HTTP Exception
    exc = HTTPException(status_code=404, detail="Item not found")
    with patch("backend.middleware.error_handler.log_event") as mock_log:
        response = await global_error_handler(mock_request, exc)
        
        assert response.status_code == 404
        import json
        body = json.loads(response.body.decode())
        assert body["type"] == "not_found"
        assert body["detail"] == "Item not found"
        mock_log.assert_called_once()

    # Test Unhandled Exception
    exc = ValueError("Something broke badly")
    with patch("backend.middleware.error_handler.log_event") as mock_log, \
         patch("backend.middleware.error_handler.logger") as mock_logger:
        response = await global_error_handler(mock_request, exc)
        
        assert response.status_code == 500
        import json
        body = json.loads(response.body.decode())
        assert body["type"] == "unknown"
        
        mock_log.assert_called_once()
        mock_logger.error.assert_called_once()
