"""Unit tests for Cricbuzz API client error handling and parsing."""

import httpx
import pytest

from backend.cricbuzz import CricbuzzAPIClient, CricbuzzResponseError, CricbuzzTimeoutError
from backend.database.models import MatchStatus


async def no_sleep(delay: float) -> None:
    return None


@pytest.mark.asyncio
async def test_fetch_live_matches_parses_cricbuzz_payload():
    payload = {
        "typeMatches": [
            {
                "seriesMatches": [
                    {
                        "seriesAdWrapper": {
                            "matches": [
                                {
                                    "matchInfo": {
                                        "matchId": 123,
                                        "team1": {"teamSName": "CSK"},
                                        "team2": {"teamSName": "MI"},
                                        "state": "In Progress",
                                        "currentBatsmen": [{"name": "Ruturaj"}, {"name": "Conway"}],
                                        "currentBowler": "Bumrah",
                                    },
                                    "matchScore": {
                                        "team1Score": {"inngs1": {"runs": 185, "wickets": 6, "overs": 20.0}},
                                        "team2Score": {"inngs1": {"runs": 120, "wickets": 3, "overs": 14.2}},
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = CricbuzzAPIClient(base_url="https://example.test", transport=transport)

    matches = await client.fetch_live_matches()

    assert len(matches) == 1
    assert matches[0].match_id == "123"
    assert matches[0].team1 == "CSK"
    assert matches[0].team2_score == "120/3"
    assert matches[0].status == MatchStatus.LIVE
    assert matches[0].current_batsmen == ["Ruturaj", "Conway"]


@pytest.mark.asyncio
async def test_fetch_commentary_parses_ball_events():
    payload = {
        "commentaryList": [
            {
                "ballNbr": "123-88",
                "overNumber": 14.4,
                "batsmanName": "Dhoni",
                "bowlerName": "Bumrah",
                "runs": 6,
                "commText": "SIX! Dhoni clears long-on.",
            }
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = CricbuzzAPIClient(base_url="https://example.test", transport=transport)

    events = await client.fetch_commentary("123")

    assert len(events) == 1
    assert events[0].match_id == "123"
    assert events[0].runs == 6
    assert events[0].batsman == "Dhoni"
    assert events[0].is_wicket is False


@pytest.mark.asyncio
async def test_timeout_retries_then_raises_timeout_error():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timeout", request=request)

    client = CricbuzzAPIClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
        max_retries=2,
        sleep=no_sleep,
    )

    with pytest.raises(CricbuzzTimeoutError):
        await client.fetch_live_matches()

    assert attempts == 2


@pytest.mark.asyncio
async def test_server_error_retries_and_recovers():
    responses = [
        httpx.Response(503, json={"error": "temporarily unavailable"}),
        httpx.Response(200, json={"matches": []}),
    ]

    def handler(request):
        return responses.pop(0)

    client = CricbuzzAPIClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
        max_retries=2,
        sleep=no_sleep,
    )

    matches = await client.fetch_live_matches()

    assert matches == []
    assert responses == []


@pytest.mark.asyncio
async def test_invalid_json_shape_raises_response_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    client = CricbuzzAPIClient(base_url="https://example.test", transport=transport, sleep=no_sleep)

    with pytest.raises(CricbuzzResponseError):
        await client.fetch_live_matches()
