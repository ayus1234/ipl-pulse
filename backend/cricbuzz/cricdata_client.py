"""
CricketData.org (CricAPI) client — alternative to Cricbuzz for live scores.

Free tier: 100 requests/day.  Endpoint: https://api.cricapi.com/v1/
Provides live scores via ``cricScore`` and match details via ``match_info``.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

try:
    from backend.database.models import BallEvent, LiveMatch, MatchStatus
except ModuleNotFoundError:
    from database.models import BallEvent, LiveMatch, MatchStatus


class CricDataAPIError(Exception):
    """Base error for CricketData API failures."""


class CricDataTimeoutError(CricDataAPIError):
    """Raised when CricketData does not respond within the configured timeout."""


class CricDataResponseError(CricDataAPIError):
    """Raised when CricketData returns an invalid status code or payload."""


class CricDataAPIClient:
    """Async client for CricketData.org (api.cricapi.com) live cricket data."""

    DEFAULT_BASE_URL = "https://api.cricapi.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
        max_retries: int = 2,
        backoff_base: float = 1.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        sleep=asyncio.sleep,
    ):
        self.api_key = api_key or os.getenv("CRICDATA_API_KEY", "")
        self.base_url = (base_url or os.getenv("CRICDATA_API_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._transport = transport
        self._sleep = sleep

        # Simple response cache: {endpoint_key: (timestamp, data)}
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = float(os.getenv("CRICDATA_CACHE_TTL", "60"))  # seconds

    # ── Public API ─────────────────────────────────────────────────

    async def fetch_live_matches(self) -> list[LiveMatch]:
        """Fetch currently live/recent matches via cricScore endpoint."""
        payload = await self._request_json("/cricScore")
        return self._parse_live_matches(payload)

    async def fetch_current_matches(self) -> list[LiveMatch]:
        """Fetch current matches with detailed score info."""
        payload = await self._request_json("/currentMatches")
        return self._parse_current_matches(payload)

    async def fetch_match_info(self, match_id: str) -> dict[str, Any]:
        """Fetch detailed match info for a specific match."""
        payload = await self._request_json(f"/match_info", extra_params={"id": match_id})
        return payload

    async def fetch_match_scorecard(self, match_id: str) -> list[BallEvent]:
        """
        CricketData.org doesn't provide ball-by-ball commentary directly.
        We synthesize BallEvents from score changes between polls.
        This method fetches match_info and creates a synthetic BallEvent
        from the latest score state.
        """
        payload = await self._request_json("/match_info", extra_params={"id": match_id})
        return self._parse_score_as_events(match_id, payload)

    # ── HTTP Layer ─────────────────────────────────────────────────

    async def _request_json(self, path: str, extra_params: dict[str, str] | None = None) -> dict[str, Any]:
        # Check cache first
        cache_key = f"{path}:{extra_params}"
        cached = self._cache.get(cache_key)
        if cached:
            ts, data = cached
            if time.time() - ts < self._cache_ttl:
                return data

        params = {"apikey": self.api_key}
        if extra_params:
            params.update(extra_params)

        last_error: Optional[Exception] = None

        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self._transport,
        ) as client:
            for attempt in range(self.max_retries):
                try:
                    url = f"{self.base_url}{path}"
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()

                    if not isinstance(payload, dict):
                        raise CricDataResponseError("CricketData response must be a JSON object")

                    # CricketData.org returns {"status": "failure", "reason": "..."} on errors
                    if payload.get("status") == "failure":
                        reason = payload.get("reason", "Unknown error")
                        raise CricDataResponseError(f"CricketData API error: {reason}")

                    # Cache the successful response
                    self._cache[cache_key] = (time.time(), payload)
                    return payload

                except httpx.TimeoutException:
                    last_error = CricDataTimeoutError(f"CricketData request timed out after {self.timeout}s")
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    last_error = CricDataResponseError(f"CricketData returned HTTP {status}")
                    if 400 <= status < 500:
                        break  # Don't retry client errors
                except CricDataResponseError:
                    raise  # Don't retry API-level errors (bad key, etc.)
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = CricDataResponseError(f"Invalid CricketData response: {exc}")

                if attempt < self.max_retries - 1:
                    await self._sleep(self.backoff_base * (2 ** attempt))

        raise last_error or CricDataAPIError("CricketData request failed")

    # ── Parsers ────────────────────────────────────────────────────

    def _parse_live_matches(self, payload: dict[str, Any]) -> list[LiveMatch]:
        """Parse cricScore response into LiveMatch models."""
        matches = []
        data = payload.get("data", [])
        if not isinstance(data, list):
            return matches

        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                matches.append(self._item_to_live_match(item))
            except Exception:
                continue  # Skip malformed entries

        return matches

    def _parse_current_matches(self, payload: dict[str, Any]) -> list[LiveMatch]:
        """Parse currentMatches response into LiveMatch models."""
        matches = []
        data = payload.get("data", [])
        if not isinstance(data, list):
            return matches

        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                matches.append(self._item_to_live_match(item))
            except Exception:
                continue

        return matches

    def _item_to_live_match(self, item: dict[str, Any]) -> LiveMatch:
        """Convert a single match item from CricketData into a LiveMatch."""
        # Extract team names
        team_info = item.get("teamInfo") or item.get("t1") and [{"shortname": item.get("t1", "")}, {"shortname": item.get("t2", "")}] or []
        if isinstance(team_info, list) and len(team_info) >= 2:
            team1 = str(team_info[0].get("shortname") or team_info[0].get("name") or "Team A")
            team2 = str(team_info[1].get("shortname") or team_info[1].get("name") or "Team B")
        else:
            # Fallback: try to parse from match name
            name = item.get("name", "Team A vs Team B")
            parts = name.split(" vs ")
            team1 = parts[0].strip() if len(parts) >= 1 else "Team A"
            team2 = parts[1].strip() if len(parts) >= 2 else "Team B"

        # Extract scores
        scores = item.get("score") or []
        team1_score = ""
        team2_score = ""
        overs = 0.0

        if isinstance(scores, list):
            for s in scores:
                if not isinstance(s, dict):
                    continue
                inning_label = str(s.get("inning", "")).lower()
                r = s.get("r", 0)
                w = s.get("w", 0)
                o = self._safe_float(s.get("o", 0))
                score_str = f"{r}/{w}"

                if team1.lower() in inning_label or "1st" in inning_label:
                    if not team1_score:
                        team1_score = score_str
                        overs = max(overs, o)
                    else:
                        team1_score = score_str  # Update with latest innings
                elif team2.lower() in inning_label or "2nd" in inning_label:
                    if not team2_score:
                        team2_score = score_str
                elif not team1_score:
                    team1_score = score_str
                    overs = max(overs, o)
                elif not team2_score:
                    team2_score = score_str

        # Also try direct score fields (cricScore format)
        if not team1_score:
            t1s = item.get("t1s", "")
            if t1s:
                team1_score = str(t1s)
        if not team2_score:
            t2s = item.get("t2s", "")
            if t2s:
                team2_score = str(t2s)

        # Parse match status
        status = self._parse_status(item.get("status", ""), item.get("matchStarted", False), item.get("matchEnded", False))

        return LiveMatch(
            match_id=str(item.get("id") or item.get("match_id") or ""),
            team1=team1,
            team2=team2,
            team1_score=team1_score,
            team2_score=team2_score,
            overs=overs,
            status=status,
            current_batsmen=[],  # Not provided by cricScore
            current_bowler="",
            last_updated=datetime.now(timezone.utc),
        )

    def _parse_score_as_events(self, match_id: str, payload: dict[str, Any]) -> list[BallEvent]:
        """
        Create synthetic BallEvents from match_info.
        Since CricketData doesn't give ball-by-ball, we create one event
        representing the current state.
        """
        events = []
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return events

        scores = data.get("score") or []
        status_text = str(data.get("status", ""))

        for i, s in enumerate(scores):
            if not isinstance(s, dict):
                continue
            r = s.get("r", 0)
            w = s.get("w", 0)
            o = self._safe_float(s.get("o", 0))
            inning = str(s.get("inning", f"Innings {i+1}"))

            events.append(BallEvent(
                ball_id=f"{match_id}-inning-{i}-{o}",
                match_id=match_id,
                over=o,
                batsman="",
                bowler="",
                runs=r,
                is_wicket=False,
                commentary=f"{inning}: {r}/{w} in {o} overs. {status_text}",
                timestamp=datetime.now(timezone.utc),
            ))

        return events

    def _parse_status(self, status_text: str, started: bool = False, ended: bool = False) -> MatchStatus:
        """Parse match status from CricketData fields."""
        text_lower = status_text.lower()

        if ended or "won" in text_lower or "result" in text_lower or "drawn" in text_lower or "tied" in text_lower:
            return MatchStatus.COMPLETED
        if "abandon" in text_lower or "no result" in text_lower:
            return MatchStatus.ABANDONED
        if started or "innings break" in text_lower or "live" in text_lower:
            return MatchStatus.LIVE
        if "preview" in text_lower or "not started" in text_lower or "upcoming" in text_lower:
            return MatchStatus.SCHEDULED

        # Default: if match has scores, it's likely live
        return MatchStatus.LIVE if started else MatchStatus.SCHEDULED

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
