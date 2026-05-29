"""Chat and social interaction service."""

import time
from typing import Dict, List, Optional
from uuid import UUID, uuid4

try:
    from backend.services.websocket_manager import WebSocketManager
    from backend.cache import CacheService, MemoryCache, generate_cache_key, CacheTTL
    from backend.database.models import ChatMessage, Reaction, utc_now
except ModuleNotFoundError:
    from services.websocket_manager import WebSocketManager
    from cache import CacheService, MemoryCache, generate_cache_key, CacheTTL
    from database.models import ChatMessage, Reaction, utc_now


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # User ID to list of timestamps
        self.requests: Dict[str, List[float]] = {}
        
    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []
            
        # Clean up old requests
        self.requests[user_id] = [t for t in self.requests[user_id] if now - t < self.window_seconds]
        
        if len(self.requests[user_id]) >= self.max_requests:
            return False
            
        self.requests[user_id].append(now)
        return True


class ChatService:
    """Handles chat messages, reactions, and room management."""
    
    def __init__(
        self, 
        ws_manager: WebSocketManager,
        cache: Optional[CacheService] = None
    ):
        self.ws = ws_manager
        self.cache = cache or MemoryCache()
        # 5 messages per user per minute limit
        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
        
    async def join_room(self, user_id: str, match_id: str, websocket):
        """Join a chat room (wrapper around WS manager)."""
        await self.ws.connect(websocket, match_id)
        
        # Send recent messages
        recent = await self.get_recent_messages(match_id)
        if recent:
            await self.ws.send_personal_message(
                {"type": "chat_history", "messages": recent}, 
                websocket
            )

    async def leave_room(self, websocket):
        """Leave a chat room."""
        self.ws.disconnect(websocket)

    async def broadcast_message(self, user_id: str, match_id: str, content: str, username: str) -> Optional[ChatMessage]:
        """Broadcast a message if not rate limited."""
        if not self.rate_limiter.is_allowed(user_id):
            return None # Rate limited
            
        message = ChatMessage(
            message_id=str(uuid4()),
            match_id=match_id,
            user_id=user_id,
            username=username,
            content=content,
            timestamp=utc_now()
        )
        
        message_dict = message.model_dump(mode="json")
        
        # Add to cache (recent 100)
        cache_key = generate_cache_key("chat", "recent", match_id)
        recent = await self.cache.get(cache_key) or []
        recent.append(message_dict)
        # Keep only last 100
        if len(recent) > 100:
            recent = recent[-100:]
            
        await self.cache.set(cache_key, recent, ttl=CacheTTL.LIVE_DATA * 360) # 1 hour
        
        # Broadcast
        await self.ws.broadcast_to_match(
            {"type": "chat_message", "data": message_dict}, 
            match_id
        )
        
        return message

    async def broadcast_reaction(self, user_id: str, match_id: str, ball_id: str, emoji: str):
        """Broadcast an emoji reaction."""
        # Rate limit reactions (allow more frequent than messages)
        # For simplicity, using the same rate limiter in this example, or bypass
        
        reaction = Reaction(
            reaction_id=str(uuid4()),
            match_id=match_id,
            ball_id=ball_id,
            user_id=user_id,
            emoji=emoji,
            timestamp=utc_now()
        )
        
        # We might aggregate reactions in real-time, but for now just broadcast
        await self.ws.broadcast_to_match(
            {"type": "reaction", "data": reaction.model_dump(mode="json")},
            match_id
        )

    async def get_recent_messages(self, match_id: str) -> List[Dict]:
        """Get recent chat messages from cache."""
        cache_key = generate_cache_key("chat", "recent", match_id)
        return await self.cache.get(cache_key) or []
