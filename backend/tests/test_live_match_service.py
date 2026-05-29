"""Unit tests for LiveMatchService polling and cache integration."""

import asyncio
from datetime import datetime, timezone

import pytest

from backend.cache import MemoryCache
from backend.database.models import BallEvent, LiveMatch, MatchStatus
from backend.rate_limiter import RateLimiter
from backend.services import LiveMatchService


class FakeCricbuzzClient:
    def __init__(self):
        self.live_calls = 0
        self.detail_calls = 0
        self.commentary_calls = 0

    async def fetch_live_matches(self):
        self.live_calls += 1
        return [
            LiveMatch(
                match_id="match-1",
                team1="CSK",
                team2="MI",
                team1_score="185/6",
                team2_score="120/3",
                overs=14.2,
                status=MatchStatus.LIVE,
                current_batsmen=["Ruturaj", "Conway"],
                current_bowler="Bumrah",
                last_updated=datetime.now(timezone.utc),
            )
        ]

    async def fetch_match_details(self, match_id: str):
        self.detail_calls += 1
        return {"match_id": match_id, "status": "live", "score": "120/3"}

    async def fetch_commentary(self, match_id: str):
        self.commentary_calls += 1
        return [
            BallEvent(
                ball_id="ball-1",
                match_id=match_id,
                over=14.2,
                batsman="Ruturaj",
                bowler="Bumrah",
                runs=4,
                is_wicket=False,
                commentary="FOUR through cover.",
                timestamp=datetime.now(timezone.utc),
            )
        ]


def build_service(client=None, broadcaster=None):
    return LiveMatchService(
        api_client=client or FakeCricbuzzClient(),
        cache=MemoryCache(),
        rate_limiter=RateLimiter(),
        broadcaster=broadcaster,
        poll_interval=60,
    )


@pytest.mark.asyncio
async def test_get_live_matches_uses_cache_first():
    client = FakeCricbuzzClient()
    service = build_service(client)

    first = await service.get_live_matches()
    second = await service.get_live_matches()

    assert client.live_calls == 1
    assert first[0].match_id == "match-1"
    assert second[0].team1 == "CSK"


@pytest.mark.asyncio
async def test_get_match_details_and_commentary_cache_independently():
    client = FakeCricbuzzClient()
    service = build_service(client)

    details_1 = await service.get_match_details("match-1")
    details_2 = await service.get_match_details("match-1")
    events_1 = await service.get_ball_by_ball("match-1")
    events_2 = await service.get_ball_by_ball("match-1")

    assert client.detail_calls == 1
    assert client.commentary_calls == 1
    assert details_1 == details_2
    assert events_1[0].commentary == events_2[0].commentary


@pytest.mark.asyncio
async def test_start_live_updates_broadcasts_polled_data():
    messages = []
    first_broadcast = None

    async def broadcaster(match_id, message):
        nonlocal first_broadcast
        messages.append((match_id, message))
        first_broadcast.set_result(True)

    first_broadcast = asyncio.get_running_loop().create_future()
    service = build_service(broadcaster=broadcaster)

    await service.start_live_updates("match-1")
    await first_broadcast
    await service.stop_live_updates("match-1")

    assert messages[0][0] == "match-1"
    assert messages[0][1]["type"] == "live_match_update"
    assert messages[0][1]["events"][0]["runs"] == 4


@pytest.mark.asyncio
async def test_start_live_updates_is_idempotent():
    service = build_service()

    await service.start_live_updates("match-1")
    first_task = service._polling_tasks["match-1"]
    await service.start_live_updates("match-1")
    second_task = service._polling_tasks["match-1"]
    await service.stop_live_updates("match-1")

    assert first_task is second_task
    assert "match-1" not in service._polling_tasks
