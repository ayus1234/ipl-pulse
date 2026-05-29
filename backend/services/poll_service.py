"""Service for handling live polls."""

from typing import Dict, List, Optional
from uuid import UUID

try:
    from backend.database.models import Poll, PollResponse
    from backend.services.websocket_manager import WebSocketManager
    from backend.cache import CacheService, MemoryCache, generate_cache_key, CacheTTL
except ModuleNotFoundError:
    from database.models import Poll, PollResponse
    from services.websocket_manager import WebSocketManager
    from cache import CacheService, MemoryCache, generate_cache_key, CacheTTL


class PollService:
    """Handles creating polls, recording responses, and real-time broadcasting."""

    def __init__(
        self,
        ws_manager: WebSocketManager,
        cache: Optional[CacheService] = None
    ):
        self.ws = ws_manager
        self.cache = cache or MemoryCache()

    async def create_poll(self, match_id: str, question: str, options: List[str]) -> Poll:
        """Create a new poll for a match and broadcast it."""
        poll = Poll(match_id=match_id, question=question, options=options)
        
        # Save poll to cache since polls are ephemeral for live matches
        poll_key = generate_cache_key("poll", poll.poll_id)
        await self.cache.set(poll_key, poll.model_dump(mode="json"), ttl=CacheTTL.LIVE_DATA * 360)
        
        # Keep track of active poll per match
        match_poll_key = generate_cache_key("poll", "active", match_id)
        await self.cache.set(match_poll_key, poll.poll_id, ttl=CacheTTL.LIVE_DATA * 360)

        # Broadcast
        await self.ws.broadcast_to_match(
            {"type": "new_poll", "data": poll.model_dump(mode="json")}, 
            match_id
        )
        return poll

    async def get_active_poll(self, match_id: str) -> Optional[Poll]:
        """Get the currently active poll for a match."""
        match_poll_key = generate_cache_key("poll", "active", match_id)
        poll_id = await self.cache.get(match_poll_key)
        if poll_id:
            poll_key = generate_cache_key("poll", poll_id)
            poll_data = await self.cache.get(poll_key)
            if poll_data:
                return Poll.model_validate(poll_data)
        return None

    async def record_response(self, poll_id: str, user_id: UUID, selected_option: str) -> Optional[Dict[str, int]]:
        """Record user response and broadcast aggregated results."""
        poll_key = generate_cache_key("poll", poll_id)
        poll_data = await self.cache.get(poll_key)
        if not poll_data:
            return None # Poll ended or not found
            
        poll = Poll.model_validate(poll_data)
        if selected_option not in poll.options:
            return None # Invalid option

        response = PollResponse(poll_id=poll_id, user_id=user_id, selected_option=selected_option)
        
        # Record response in cache list
        responses_key = generate_cache_key("poll", poll_id, "responses")
        responses = await self.cache.get(responses_key) or []
        
        # Check if user already voted (replace vote)
        responses = [r for r in responses if r.get("user_id") != str(user_id)]
        responses.append(response.model_dump(mode="json"))
        
        await self.cache.set(responses_key, responses, ttl=CacheTTL.LIVE_DATA * 360)

        # Aggregate results
        results = {opt: 0 for opt in poll.options}
        for r in responses:
            opt = r.get("selected_option")
            if opt in results:
                results[opt] += 1
                
        # Broadcast results updates
        await self.ws.broadcast_to_match(
            {"type": "poll_results", "poll_id": poll_id, "results": results},
            poll.match_id
        )
        
        return results
