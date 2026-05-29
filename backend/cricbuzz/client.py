"""
Cricbuzz API client.

The client is intentionally small and transport-injectable so tests can use
httpx.MockTransport without touching the network.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import httpx

try:
    from backend.database.models import BallEvent, LiveMatch, MatchStatus
except ModuleNotFoundError:  # Allows imports when running from the backend dir.
    from database.models import BallEvent, LiveMatch, MatchStatus


class CricbuzzAPIError(Exception):
    """Base error for Cricbuzz API failures."""


class CricbuzzTimeoutError(CricbuzzAPIError):
    """Raised when Cricbuzz does not respond within the configured timeout."""


class CricbuzzResponseError(CricbuzzAPIError):
    """Raised when Cricbuzz returns an invalid status code or payload."""


class CricbuzzAPIClient:
    """Async client for live matches, match details, and commentary."""

    DEFAULT_BASE_URL = "https://cricbuzz-cricket.p.rapidapi.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
        backoff_base: float = 1.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        sleep=asyncio.sleep,
    ):
        self.api_key = api_key or os.getenv("CRICBUZZ_API_KEY") or os.getenv("RAPIDAPI_KEY")
        self.base_url = (base_url or os.getenv("CRICBUZZ_API_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._transport = transport
        self._sleep = sleep

    async def fetch_live_matches(self) -> list[LiveMatch]:
        """Fetch and parse currently live matches."""
        payload = await self._request_json("/matches/v1/live")
        return self.parse_live_matches(payload)

    async def fetch_match_details(self, match_id: str) -> dict[str, Any]:
        """Fetch raw details for a specific match."""
        return await self._request_json(f"/mcenter/v1/{match_id}")

    async def fetch_commentary(self, match_id: str) -> list[BallEvent]:
        """Fetch and parse ball-by-ball commentary for a match."""
        payload = await self._request_json(f"/mcenter/v1/{match_id}/comm")
        return self.parse_commentary(match_id, payload)

    async def _request_json(self, path: str) -> dict[str, Any]:
        headers = self._headers()
        last_error: Optional[Exception] = None

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self._transport,
            headers=headers,
        ) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(path)
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise CricbuzzResponseError("Cricbuzz response must be a JSON object")
                    return payload
                except httpx.TimeoutException as exc:
                    last_error = CricbuzzTimeoutError(f"Cricbuzz request timed out after {self.timeout}s")
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    last_error = CricbuzzResponseError(f"Cricbuzz returned HTTP {status}")
                    if 400 <= status < 500:
                        break  # Don't retry client errors including 429 rate limit
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = CricbuzzResponseError(f"Invalid Cricbuzz response: {exc}")

                if attempt < self.max_retries - 1:
                    await self._sleep(self.backoff_base * (2**attempt))

        raise last_error or CricbuzzAPIError("Cricbuzz request failed")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-RapidAPI-Key"] = self.api_key
            headers["X-RapidAPI-Host"] = os.getenv("CRICBUZZ_API_HOST", "cricbuzz-cricket.p.rapidapi.com")
        return headers

    def parse_live_matches(self, payload: dict[str, Any]) -> list[LiveMatch]:
        """Parse common Cricbuzz live-match payloads into LiveMatch models."""
        matches = []
        for item in self._iter_match_items(payload):
            match_info = item.get("matchInfo", item)
            match_score = item.get("matchScore", {})
            matches.append(self._parse_live_match(match_info, match_score))
        return matches

    def parse_commentary(self, match_id: str, payload: dict[str, Any]) -> list[BallEvent]:
        """Parse common Cricbuzz commentary payloads into BallEvent models."""
        raw_items = payload.get("commentaryList") or payload.get("commentary") or payload.get("comments") or []
        events = []
        
        # New RapidAPI format uses comwrapper
        if not raw_items and "comwrapper" in payload:
            wrapper = payload.get("comwrapper", [])
            for item in wrapper:
                if "commentary" in item:
                    comm = item["commentary"]
                    over = self._safe_float(comm.get("overnum"))
                    
                    # Try to extract batsman and bowler names from commentary formats if available
                    batsman, bowler = "", ""
                    formats = comm.get("commentaryformats", [])
                    if isinstance(formats, list):
                        for f in formats:
                            # Usually formats contain bold text for batsman/bowler like "B0\B1"
                            # We'll just rely on parsing the commtxt for runs/wickets
                            pass
                    
                    text = str(comm.get("commtxt") or "")
                    if not text:
                        continue
                        
                    # Extract runs/wickets from text if not provided directly
                    runs = 0
                    is_wicket = "out" in text.lower() or "wicket" in text.lower()
                    if "SIX" in text:
                        runs = 6
                    elif "FOUR" in text or "4 runs" in text:
                        runs = 4
                    elif "1 run" in text:
                        runs = 1
                    elif "2 runs" in text:
                        runs = 2
                    elif "3 runs" in text:
                        runs = 3
                        
                    events.append(BallEvent(
                        ball_id=f"{match_id}-{len(events)}",
                        match_id=match_id,
                        over=over,
                        batsman=batsman,
                        bowler=bowler,
                        runs=runs,
                        is_wicket=is_wicket,
                        commentary=text,
                        timestamp=datetime.now(timezone.utc),
                    ))
            
            # The newest events are usually first in comwrapper, so we reverse it to chronological order
            events.reverse()
            return events

        for index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            events.append(self._parse_ball_event(match_id, item, index))
        return events

    def _iter_match_items(self, payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
        if isinstance(payload.get("matches"), list):
            for match in payload["matches"]:
                if isinstance(match, dict):
                    yield match
            return

        for type_match in payload.get("typeMatches", []):
            for series_match in type_match.get("seriesMatches", []):
                wrapper = series_match.get("seriesAdWrapper") or series_match.get("seriesWrapper") or {}
                for match in wrapper.get("matches", []):
                    if isinstance(match, dict):
                        yield match

    def _parse_live_match(self, info: dict[str, Any], score: dict[str, Any]) -> LiveMatch:
        team1 = self._team_name(info.get("team1"))
        team2 = self._team_name(info.get("team2"))
        return LiveMatch(
            match_id=str(info.get("matchId") or info.get("match_id") or ""),
            team1=team1,
            team2=team2,
            team1_score=self._format_team_score(score.get("team1Score")),
            team2_score=self._format_team_score(score.get("team2Score")),
            overs=self._current_overs(score),
            status=self._parse_status(info.get("state") or info.get("status")),
            current_batsmen=self._current_batsmen(info),
            current_bowler=str(info.get("currentBowler") or info.get("bowler") or ""),
            last_updated=datetime.now(timezone.utc),
        )

    def _parse_ball_event(self, match_id: str, item: dict[str, Any], index: int) -> BallEvent:
        over = self._safe_float(item.get("overNumber") or item.get("over") or item.get("overs"))
        runs = self._safe_int(item.get("runs") or item.get("batRuns") or 0)
        commentary = str(item.get("commText") or item.get("commentary") or item.get("text") or "")
        is_wicket = bool(item.get("isWicket") or item.get("wicket") or "wicket" in commentary.lower())
        return BallEvent(
            ball_id=str(item.get("ballNbr") or item.get("ball_id") or f"{match_id}-{index}"),
            match_id=match_id,
            over=over,
            batsman=str(item.get("batsman") or item.get("batsmanName") or ""),
            bowler=str(item.get("bowler") or item.get("bowlerName") or ""),
            runs=runs,
            is_wicket=is_wicket,
            commentary=commentary,
            timestamp=datetime.now(timezone.utc),
        )

    def _team_name(self, team: Any) -> str:
        if isinstance(team, dict):
            return str(team.get("teamSName") or team.get("teamName") or team.get("name") or "")
        return str(team or "")

    def _format_team_score(self, score: Any) -> str:
        if not isinstance(score, dict):
            return ""
        innings = score.get("inngs1") or score.get("innings1") or score
        runs = innings.get("runs")
        wickets = innings.get("wickets", 0)
        if runs is None:
            return ""
        return f"{runs}/{wickets}"

    def _current_overs(self, score: dict[str, Any]) -> float:
        for key in ("team1Score", "team2Score"):
            innings = (score.get(key) or {}).get("inngs1") or score.get(key) or {}
            overs = innings.get("overs")
            if overs is not None:
                return self._safe_float(overs)
        return 0.0

    def _current_batsmen(self, info: dict[str, Any]) -> list[str]:
        batsmen = info.get("currentBatsmen") or info.get("batsmen") or []
        if isinstance(batsmen, list):
            return [str(player.get("name") if isinstance(player, dict) else player) for player in batsmen][:2]
        return []

    def _parse_status(self, value: Any) -> MatchStatus:
        status = str(value or "").lower()
        if "complete" in status or status in {"completed", "result"}:
            return MatchStatus.COMPLETED
        if "abandon" in status:
            return MatchStatus.ABANDONED
        if "preview" in status or "schedule" in status or "upcoming" in status:
            return MatchStatus.SCHEDULED
        return MatchStatus.LIVE

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
