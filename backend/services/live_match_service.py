"""Live match service for cache-first Cricbuzz integration and polling."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any, Awaitable, Callable, Optional

try:
    from backend.cache import CacheService, CacheTTL, MemoryCache, generate_cache_key
    from backend.cricbuzz import CricbuzzAPIClient
    from backend.database.models import BallEvent, LiveMatch, MatchStatus
    from backend.rate_limiter import RateLimiter
except ModuleNotFoundError:  # Allows imports when running from the backend dir.
    from cache import CacheService, CacheTTL, MemoryCache, generate_cache_key
    from cricbuzz import CricbuzzAPIClient
    from database.models import BallEvent, LiveMatch, MatchStatus
    from rate_limiter import RateLimiter


BroadcastCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class LiveMatchService:
    """Coordinates live match fetching, caching, rate limiting, and polling."""

    def __init__(
        self,
        api_client: Optional[CricbuzzAPIClient] = None,
        cache: Optional[CacheService] = None,
        rate_limiter: Optional[RateLimiter] = None,
        broadcaster: Optional[BroadcastCallback] = None,
        match_history_repo=None,
        poll_interval: float = 10.0,
        sleep=asyncio.sleep,
    ):
        self.api_client = api_client or CricbuzzAPIClient()
        self.cache = cache or MemoryCache()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.broadcaster = broadcaster
        self.match_history_repo = match_history_repo
        self.poll_interval = poll_interval
        self._sleep = sleep
        self._polling_tasks: dict[str, asyncio.Task] = {}
        self.rate_limiter.configure("cricbuzz_api", max_requests=6, time_window=60)

    async def get_live_matches(self) -> list[LiveMatch]:
        """Get live matches using cache-first retrieval."""
        cache_key = generate_cache_key("matches", suffix="live")
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return [LiveMatch.model_validate(match) for match in cached]

        matches = await self._fetch_with_limit(self.api_client.fetch_live_matches)
        await self._persist_completed_matches(matches)
        await self.cache.set(
            cache_key,
            [match.model_dump(mode="json") for match in matches],
            ttl=CacheTTL.LIVE_DATA,
        )
        return matches

    async def persist_completed_match(self, match: LiveMatch):
        """Persist a completed live match to the match history repository."""
        if not self.match_history_repo or match.status != MatchStatus.COMPLETED:
            return None

        payload = {
            "match_id": match.match_id,
            "match_type": "live",
            "team1": match.team1,
            "team2": match.team2,
            "winner": None,
            "final_score_team1": match.team1_score,
            "final_score_team2": match.team2_score,
            "match_date": match.last_updated,
            "status": match.status.value,
        }

        existing = await self.match_history_repo.find_by_id(match.match_id, "match_id")
        if existing:
            update_payload = {key: value for key, value in payload.items() if key != "match_id"}
            return await self.match_history_repo.update(match.match_id, update_payload, "match_id")
        return await self.match_history_repo.create(payload)

    async def get_match_details(self, match_id: str) -> dict[str, Any]:
        """Get raw details for a match using cache-first retrieval."""
        cache_key = generate_cache_key("match", match_id, "details")
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached

        details = await self._fetch_with_limit(lambda: self.api_client.fetch_match_details(match_id))
        await self.cache.set(cache_key, details, ttl=CacheTTL.LIVE_DATA)
        return details

    async def get_ball_by_ball(self, match_id: str) -> list[BallEvent]:
        """Get ball-by-ball events for a match using cache-first retrieval."""
        cache_key = generate_cache_key("match", match_id, "commentary")
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return [BallEvent.model_validate(event) for event in cached]

        events = await self._fetch_with_limit(lambda: self.api_client.fetch_commentary(match_id))
        await self.cache.set(
            cache_key,
            [event.model_dump(mode="json") for event in events],
            ttl=CacheTTL.LIVE_DATA,
        )
        return events

    async def start_live_updates(self, match_id: str) -> None:
        """Start periodic polling for a live match."""
        if match_id in self._polling_tasks and not self._polling_tasks[match_id].done():
            return
        self._polling_tasks[match_id] = asyncio.create_task(self._poll_match(match_id))

    async def stop_live_updates(self, match_id: str) -> None:
        """Stop periodic polling for a live match."""
        task = self._polling_tasks.pop(match_id, None)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def stop_all_live_updates(self) -> None:
        """Stop all polling tasks."""
        match_ids = list(self._polling_tasks)
        for match_id in match_ids:
            await self.stop_live_updates(match_id)

    async def _fetch_with_limit(self, fetcher):
        if not await self.rate_limiter.acquire("cricbuzz_api"):
            await self.rate_limiter.queue_request("cricbuzz_api")
        return await fetcher()

    async def _persist_completed_matches(self, matches: list[LiveMatch]) -> None:
        for match in matches:
            await self.persist_completed_match(match)

    async def _poll_match(self, match_id: str) -> None:
        while True:
            details = await self.get_match_details(match_id)
            events = await self.get_ball_by_ball(match_id)
            await self._broadcast(
                match_id,
                {
                    "type": "live_match_update",
                    "match_id": match_id,
                    "details": details,
                    "events": [event.model_dump(mode="json") for event in events],
                },
            )
            await self._sleep(self.poll_interval)

    async def _broadcast(self, match_id: str, message: dict[str, Any]) -> None:
        if self.broadcaster:
            await self.broadcaster(match_id, message)
