"""Service for retrieving match schedules, history, and highlights."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

try:
    from backend.database.models import MatchStatus, MatchHistory, BallEvent
    from backend.database.repository import MatchHistoryRepository
    from backend.cricbuzz import CricbuzzAPIClient
except ModuleNotFoundError:
    from database.models import MatchStatus, MatchHistory, BallEvent
    from database.repository import MatchHistoryRepository
    from cricbuzz import CricbuzzAPIClient

class MatchService:
    """Coordinates match schedule, history, and highlights retrieval."""

    def __init__(
        self,
        match_repo: MatchHistoryRepository,
        api_client: Optional[CricbuzzAPIClient] = None
    ):
        self.match_repo = match_repo
        self.api_client = api_client or CricbuzzAPIClient()

    async def get_schedule(self) -> List[Dict[str, Any]]:
        """Get all scheduled (upcoming) matches."""
        # Find matches with status SCHEDULED
        # Or from cricbuzz if not in DB, but requirement says "fetch from database"
        matches = await self.match_repo.find_by_status(MatchStatus.SCHEDULED.value)
        # Ensure chronological ordering (oldest scheduled match first)
        matches.sort(key=lambda x: x.get("match_date", datetime.min.replace(tzinfo=timezone.utc)))
        return matches

    async def get_history(self) -> List[Dict[str, Any]]:
        """Get all completed matches."""
        matches = await self.match_repo.find_by_status(MatchStatus.COMPLETED.value)
        # Ensure chronological ordering (newest completed match first)
        matches.sort(key=lambda x: x.get("match_date", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return matches

    async def get_match_highlights(self, match_id: str) -> List[Dict[str, Any]]:
        """Get highlights (wickets, boundaries, sixes) for a specific match."""
        # Ball events are retrieved from cricbuzz or cached
        # In a real app we would store them in a DB. For now, we fetch from API.
        events = await self.api_client.fetch_commentary(match_id)
        
        # Filter highlights: wickets, fours, sixes
        highlights = [
            event.model_dump(mode="json") for event in events
            if event.is_wicket or event.runs >= 4
        ]
        return highlights
