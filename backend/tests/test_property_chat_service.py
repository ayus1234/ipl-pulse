"""Property tests for ChatService and WebSocketManager."""

import pytest
import asyncio
from hypothesis import given, settings, strategies as st
from uuid import uuid4

from backend.services.websocket_manager import WebSocketManager
from backend.services.chat_service import ChatService


class MockWebSocket:
    """Mock WebSocket for testing."""
    def __init__(self):
        self.accepted = False
        self.messages = []
        
    async def accept(self):
        self.accepted = True
        
    async def send_json(self, data):
        self.messages.append(data)


# Feature: ipl-live-score-integration, Property 15: Chat room connection
@pytest.mark.asyncio
async def test_chat_room_connection():
    """
    **Validates: Requirements 5.1**
    
    Property: A user can join a room and receive the most recent messages.
    """
    ws_manager = WebSocketManager()
    chat_service = ChatService(ws_manager)
    
    # Pre-populate some messages
    match_id = "match123"
    await chat_service.broadcast_message(str(uuid4()), match_id, "Hello!", "user1")
    
    ws = MockWebSocket()
    await chat_service.join_room("user2", match_id, ws)
    
    assert ws.accepted
    assert ws in ws_manager.active_connections[match_id]
    
    # Verify received history
    assert len(ws.messages) == 1
    assert ws.messages[0]["type"] == "chat_history"
    assert len(ws.messages[0]["messages"]) == 1
    assert ws.messages[0]["messages"][0]["content"] == "Hello!"


# Feature: ipl-live-score-integration, Property 16: Room broadcast delivery
@given(
    messages=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.asyncio
async def test_room_broadcast_delivery(messages):
    """
    **Validates: Requirements 5.3, 5.5**
    
    Property: Messages broadcast to a room are delivered to all active connections.
    """
    ws_manager = WebSocketManager()
    chat_service = ChatService(ws_manager)
    
    match_id = "test_match"
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    await chat_service.join_room("u1", match_id, ws1)
    await chat_service.join_room("u2", match_id, ws2)
    
    # Clear history messages sent on join
    ws1.messages.clear()
    ws2.messages.clear()
    
    for msg in messages:
        # Avoid rate limiting by using different user or spacing, but here we just bypass or use different users if needed.
        # Actually our rate limiter is 5 per minute, if list is <=5 we are fine.
        await chat_service.broadcast_message(str(uuid4()), match_id, msg, "user")
        
    assert len(ws1.messages) == len(messages)
    assert len(ws2.messages) == len(messages)
    
    for i, msg in enumerate(messages):
        assert ws1.messages[i]["type"] == "chat_message"
        assert ws1.messages[i]["data"]["content"] == msg


# Feature: ipl-live-score-integration, Property 17: Emoji reaction support
@given(
    emoji=st.sampled_from(["👍", "❤️", "🔥", "😂", "🏏"])
)
@settings(max_examples=10, deadline=None)
@pytest.mark.asyncio
async def test_emoji_reaction_support(emoji):
    """
    **Validates: Requirements 5.4**
    """
    ws_manager = WebSocketManager()
    chat_service = ChatService(ws_manager)
    
    match_id = "react_match"
    ws = MockWebSocket()
    await chat_service.join_room("u1", match_id, ws)
    ws.messages.clear()
    
    await chat_service.broadcast_reaction(str(uuid4()), match_id, "ball_1_1", emoji)
    
    assert len(ws.messages) == 1
    assert ws.messages[0]["type"] == "reaction"
    assert ws.messages[0]["data"]["emoji"] == emoji


# Feature: ipl-live-score-integration, Property 25: WebSocket reconnection with backoff
@pytest.mark.asyncio
async def test_websocket_reconnection_state_cleanup():
    """
    **Validates: Requirements 9.2**
    
    Simulates disconnection and cleanup, ensuring state is ready for reconnection.
    """
    ws_manager = WebSocketManager()
    
    match_id = "reconnect_match"
    ws = MockWebSocket()
    await ws_manager.connect(ws, match_id)
    
    assert ws in ws_manager.active_connections[match_id]
    
    # Simulate disconnect
    ws_manager.disconnect(ws)
    
    assert match_id not in ws_manager.active_connections or ws not in ws_manager.active_connections[match_id]
    assert ws not in ws_manager.connection_to_match
    
    # Should be able to reconnect cleanly
    ws_new = MockWebSocket()
    await ws_manager.connect(ws_new, match_id)
    assert ws_new in ws_manager.active_connections[match_id]
