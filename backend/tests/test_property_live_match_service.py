"""Property tests for LiveMatchService live data contracts."""

from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

from backend.cache import MemoryCache
from backend.database.models import LiveMatch, MatchStatus
from backend.rate_limiter import RateLimiter
from backend.services import LiveMatchService


def score_strategy():
    return st.builds(
        lambda runs, wickets: f"{runs}/{wickets}",
        st.integers(min_value=0, max_value=300),
        st.integers(min_value=0, max_value=10),
    )


def live_match_strategy(status=MatchStatus.LIVE):
    text = st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"),
    )
    return st.builds(
        LiveMatch,
        match_id=text,
        team1=text,
        team2=text,
        team1_score=score_strategy(),
        team2_score=score_strategy(),
        overs=st.floats(min_value=0, max_value=20, allow_nan=False, allow_infinity=False),
        status=st.just(status),
        current_batsmen=st.lists(text, min_size=1, max_size=2),
        current_bowler=text,
        last_updated=st.just(datetime.now(timezone.utc)),
    )


class FakeMatchHistoryRepo:
    def __init__(self):
        self.rows = {}

    async def find_by_id(self, id_value, id_column="match_id"):
        return self.rows.get(id_value)

    async def create(self, data):
        self.rows[data["match_id"]] = dict(data)
        return self.rows[data["match_id"]]

    async def update(self, id_value, data, id_column="match_id"):
        self.rows[id_value].update(data)
        return self.rows[id_value]


# Feature: ipl-live-score-integration, Property 1: Live match display completeness
@given(match=live_match_strategy())
@settings(max_examples=20, deadline=None)
def test_live_match_serialization_contains_display_fields(match):
    """
    **Validates: Requirements 1.5**

    Property: Any live match exposed by the backend contains the fields needed
    to render team names, scores, overs, current players, and status.
    """
    data = match.model_dump(mode="json")

    for field in (
        "team1",
        "team2",
        "team1_score",
        "team2_score",
        "overs",
        "current_batsmen",
        "current_bowler",
        "status",
    ):
        assert field in data
        assert data[field] not in (None, "")


# Feature: ipl-live-score-integration, Property 3: Match completion persistence
@given(match=live_match_strategy(status=MatchStatus.COMPLETED))
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_completed_match_is_persisted_to_match_history(match):
    """
    **Validates: Requirements 1.7**

    Property: Any completed live match passed to the service is marked completed
    and stored with final scores in the match history data store.
    """
    repo = FakeMatchHistoryRepo()
    service = LiveMatchService(
        cache=MemoryCache(),
        rate_limiter=RateLimiter(),
        match_history_repo=repo,
    )

    persisted = await service.persist_completed_match(match)

    assert persisted["match_id"] == match.match_id
    assert persisted["match_type"] == "live"
    assert persisted["status"] == MatchStatus.COMPLETED.value
    assert persisted["final_score_team1"] == match.team1_score
    assert persisted["final_score_team2"] == match.team2_score
    assert repo.rows[match.match_id] == persisted
