"""Service for handling player statistics and team standings."""

from typing import List, Dict, Any, Optional

try:
    from backend.database.models import PlayerStats, TeamStanding
    from backend.database.repository import PlayerStatsRepository, TeamStandingRepository
    from backend.cache import CacheService, CacheTTL, generate_cache_key, MemoryCache
except ModuleNotFoundError:
    from database.models import PlayerStats, TeamStanding
    from database.repository import PlayerStatsRepository, TeamStandingRepository
    from cache import CacheService, CacheTTL, generate_cache_key, MemoryCache


class StatisticsService:
    """Handles logic for player statistics and team standings."""

    def __init__(
        self,
        player_repo: PlayerStatsRepository,
        team_repo: TeamStandingRepository,
        cache: Optional[CacheService] = None
    ):
        self.player_repo = player_repo
        self.team_repo = team_repo
        self.cache = cache or MemoryCache()

    async def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        """Get stats for a specific player."""
        cache_key = generate_cache_key("stats", "player", player_id)
        cached = await self.cache.get(cache_key)
        if cached:
            return PlayerStats.model_validate(cached)

        stats_dict = await self.player_repo.find_by_id(player_id, "player_id")
        if stats_dict:
            stats = PlayerStats.model_validate(stats_dict)
            await self.cache.set(cache_key, stats.model_dump(mode="json"), ttl=CacheTTL.HISTORICAL)
            return stats
        return None

    async def get_top_run_scorers(self, limit: int = 10) -> List[PlayerStats]:
        """Get top run scorers."""
        cache_key = generate_cache_key("stats", "top", "batsmen", limit)
        cached = await self.cache.get(cache_key)
        if cached:
            return [PlayerStats.model_validate(p) for p in cached]

        stats_list = await self.player_repo.get_top_scorers(limit)
        stats = [PlayerStats.model_validate(p) for p in stats_list]
        await self.cache.set(cache_key, [s.model_dump(mode="json") for s in stats], ttl=CacheTTL.STATISTICS)
        return stats

    async def get_top_wicket_takers(self, limit: int = 10) -> List[PlayerStats]:
        """Get top wicket takers."""
        cache_key = generate_cache_key("stats", "top", "bowlers", limit)
        cached = await self.cache.get(cache_key)
        if cached:
            return [PlayerStats.model_validate(p) for p in cached]

        stats_list = await self.player_repo.get_top_wicket_takers(limit)
        stats = [PlayerStats.model_validate(p) for p in stats_list]
        await self.cache.set(cache_key, [s.model_dump(mode="json") for s in stats], ttl=CacheTTL.STATISTICS)
        return stats

    async def get_team_standings(self, season: str = "2024") -> List[TeamStanding]:
        """Get team standings for a season."""
        cache_key = generate_cache_key("stats", "standings", season)
        cached = await self.cache.get(cache_key)
        if cached:
            return [TeamStanding.model_validate(t) for t in cached]

        standings_list = await self.team_repo.find_by_season(season)
        standings = [TeamStanding.model_validate(t) for t in standings_list]
        
        # Calculate rank dynamically
        # Python uses 0-indexed enumerate, so rank is i+1
        for i, s in enumerate(standings):
            # Rank isn't stored in DB directly to avoid constant updating of all rows
            pass

        await self.cache.set(cache_key, [s.model_dump(mode="json") for s in standings], ttl=CacheTTL.STATISTICS)
        return standings

    async def update_player_stats(self, player_id: str, runs: int = 0, wickets: int = 0, balls_faced: int = 0, balls_bowled: int = 0, runs_conceded: int = 0) -> Optional[PlayerStats]:
        """Update player statistics."""
        # Simple incremental update
        query = """
            UPDATE player_stats 
            SET runs_scored = runs_scored + $2,
                wickets_taken = wickets_taken + $3,
                balls_faced = balls_faced + $4,
                balls_bowled = balls_bowled + $5,
                runs_conceded = runs_conceded + $6,
                updated_at = CURRENT_TIMESTAMP
            WHERE player_id = $1
            RETURNING *
        """
        updated_dict = await self.player_repo.db.fetch_one(
            query, player_id, runs, wickets, balls_faced, balls_bowled, runs_conceded
        )
        if updated_dict:
            # Invalidate caches
            await self.cache.delete(generate_cache_key("stats", "player", player_id))
            await self.cache.delete(generate_cache_key("stats", "top", "batsmen", 10))
            await self.cache.delete(generate_cache_key("stats", "top", "bowlers", 10))
            return PlayerStats.model_validate(updated_dict)
        return None

    async def update_team_standings_after_match(self, team_name: str, season: str, won: bool, runs_scored: int, runs_conceded: int, overs_faced: float, overs_bowled: float) -> Optional[TeamStanding]:
        """Update team standings and recalculate NRR after a match."""
        updated = await self.team_repo.update_after_match(
            team_name, season, won, runs_scored, runs_conceded, overs_faced, overs_bowled
        )
        if updated:
            await self.cache.delete(generate_cache_key("stats", "standings", season))
            return TeamStanding.model_validate(updated)
        return None
