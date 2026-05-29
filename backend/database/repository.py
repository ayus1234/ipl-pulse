"""
Base repository pattern for database operations
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from .connection import DatabaseManager
from .models import (
    User,
    Prediction,
    MatchHistory,
    PlayerStats,
    TeamStanding,
    Achievement,
)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.
    
    This implements the repository pattern to abstract database operations
    and provide a clean interface for data access.
    """

    def __init__(self, db: DatabaseManager, table_name: str):
        """
        Initialize repository.
        
        Args:
            db: DatabaseManager instance
            table_name: Name of the database table
        """
        self.db = db
        self.table_name = table_name

    async def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[Dict]:
        """
        Find a record by ID.
        
        Args:
            id_value: ID value to search for
            id_column: Name of the ID column
            
        Returns:
            Record as dict or None
        """
        query = f"SELECT * FROM {self.table_name} WHERE {id_column} = $1"
        return await self.db.fetch_one(query, id_value)

    async def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        Find all records.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of records as dicts
        """
        query = f"SELECT * FROM {self.table_name}"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        return await self.db.fetch_all(query)

    async def create(self, data: Dict[str, Any]) -> Dict:
        """
        Create a new record.
        
        Args:
            data: Record data as dict
            
        Returns:
            Created record as dict
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f"${i+1}" for i in range(len(data))])
        values = list(data.values())
        
        query = f"""
            INSERT INTO {self.table_name} ({columns})
            VALUES ({placeholders})
            RETURNING *
        """
        return await self.db.fetch_one(query, *values)

    async def update(
        self, id_value: Any, data: Dict[str, Any], id_column: str = "id"
    ) -> Optional[Dict]:
        """
        Update a record by ID.
        
        Args:
            id_value: ID value to update
            data: Updated data as dict
            id_column: Name of the ID column
            
        Returns:
            Updated record as dict or None
        """
        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(data.keys())])
        values = [id_value] + list(data.values())
        
        query = f"""
            UPDATE {self.table_name}
            SET {set_clause}
            WHERE {id_column} = $1
            RETURNING *
        """
        return await self.db.fetch_one(query, *values)

    async def delete(self, id_value: Any, id_column: str = "id") -> bool:
        """
        Delete a record by ID.
        
        Args:
            id_value: ID value to delete
            id_column: Name of the ID column
            
        Returns:
            True if deleted, False otherwise
        """
        query = f"DELETE FROM {self.table_name} WHERE {id_column} = $1"
        try:
            await self.db.execute(query, id_value)
            return True
        except Exception:
            return False


class UserRepository(BaseRepository[User]):
    """Repository for User operations"""

    def __init__(self, db: DatabaseManager):
        super().__init__(db, "users")

    async def find_by_username(self, username: str) -> Optional[Dict]:
        """Find user by username"""
        query = "SELECT * FROM users WHERE username = $1"
        return await self.db.fetch_one(query, username)

    async def find_by_email(self, email: str) -> Optional[Dict]:
        """Find user by email"""
        query = "SELECT * FROM users WHERE email = $1"
        return await self.db.fetch_one(query, email)

    async def update_xp(self, user_id: UUID, xp_delta: int) -> Optional[Dict]:
        """
        Update user's total XP.
        
        Args:
            user_id: User ID
            xp_delta: Amount to add to XP (can be negative)
            
        Returns:
            Updated user record
        """
        query = """
            UPDATE users
            SET total_xp = total_xp + $2
            WHERE user_id = $1
            RETURNING *
        """
        return await self.db.fetch_one(query, str(user_id), xp_delta)


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for Prediction operations"""

    def __init__(self, db: DatabaseManager):
        super().__init__(db, "predictions")

    async def find_by_user(
        self, user_id: UUID, match_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Find predictions by user.
        
        Args:
            user_id: User ID
            match_type: Optional filter by match type
            
        Returns:
            List of predictions
        """
        if match_type:
            query = """
                SELECT * FROM predictions
                WHERE user_id = $1 AND match_type = $2
                ORDER BY created_at DESC
            """
            return await self.db.fetch_all(query, str(user_id), match_type)
        else:
            query = """
                SELECT * FROM predictions
                WHERE user_id = $1
                ORDER BY created_at DESC
            """
            return await self.db.fetch_all(query, str(user_id))

    async def find_by_match(self, match_id: str) -> List[Dict]:
        """Find predictions for a specific match"""
        query = """
            SELECT * FROM predictions
            WHERE match_id = $1
            ORDER BY created_at DESC
        """
        return await self.db.fetch_all(query, match_id)

    async def get_user_streak(self, user_id: UUID, match_type: str) -> int:
        """
        Get user's current prediction streak.
        
        Args:
            user_id: User ID
            match_type: Match type to check
            
        Returns:
            Current streak count
        """
        query = """
            SELECT is_correct FROM predictions
            WHERE user_id = $1 AND match_type = $2 AND is_correct IS NOT NULL
            ORDER BY evaluated_at DESC
            LIMIT 10
        """
        results = await self.db.fetch_all(query, str(user_id), match_type)
        
        streak = 0
        for result in results:
            if result.get("is_correct"):
                streak += 1
            else:
                break
        return streak


class MatchHistoryRepository(BaseRepository[MatchHistory]):
    """Repository for MatchHistory operations"""

    def __init__(self, db: DatabaseManager):
        super().__init__(db, "match_history")

    async def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Find matches within a date range"""
        query = """
            SELECT * FROM match_history
            WHERE match_date BETWEEN $1 AND $2
            ORDER BY match_date ASC
        """
        return await self.db.fetch_all(query, start_date, end_date)

    async def find_by_status(self, status: str) -> List[Dict]:
        """Find matches by status"""
        query = """
            SELECT * FROM match_history
            WHERE status = $1
            ORDER BY match_date DESC
        """
        return await self.db.fetch_all(query, status)

    async def find_by_team(self, team_name: str) -> List[Dict]:
        """Find matches involving a specific team"""
        query = """
            SELECT * FROM match_history
            WHERE team1 = $1 OR team2 = $1
            ORDER BY match_date DESC
        """
        return await self.db.fetch_all(query, team_name)


class PlayerStatsRepository(BaseRepository[PlayerStats]):
    """Repository for PlayerStats operations"""

    def __init__(self, db: DatabaseManager):
        super().__init__(db, "player_stats")

    async def find_by_team(self, team: str) -> List[Dict]:
        """Find player stats by team"""
        query = """
            SELECT * FROM player_stats
            WHERE team = $1
            ORDER BY runs_scored DESC
        """
        return await self.db.fetch_all(query, team)

    async def get_top_scorers(self, limit: int = 10) -> List[Dict]:
        """Get top run scorers"""
        query = """
            SELECT * FROM player_stats
            ORDER BY runs_scored DESC
            LIMIT $1
        """
        return await self.db.fetch_all(query, limit)

    async def get_top_wicket_takers(self, limit: int = 10) -> List[Dict]:
        """Get top wicket takers"""
        query = """
            SELECT * FROM player_stats
            WHERE wickets_taken > 0
            ORDER BY wickets_taken DESC
            LIMIT $1
        """
        return await self.db.fetch_all(query, limit)


class TeamStandingRepository(BaseRepository[TeamStanding]):
    """Repository for TeamStanding operations"""

    def __init__(self, db: DatabaseManager):
        super().__init__(db, "team_standings")

    async def find_by_season(self, season: str) -> List[Dict]:
        """Find team standings for a season"""
        query = """
            SELECT * FROM team_standings
            WHERE season = $1
            ORDER BY points DESC, net_run_rate DESC
        """
        return await self.db.fetch_all(query, season)

    async def update_after_match(
        self,
        team_name: str,
        season: str,
        won: bool,
        runs_scored: int,
        runs_conceded: int,
        overs_faced: float,
        overs_bowled: float,
    ) -> Optional[Dict]:
        """
        Update team standings after a match.
        
        Args:
            team_name: Team name
            season: Season
            won: Whether team won
            runs_scored: Runs scored by team
            runs_conceded: Runs conceded by team
            overs_faced: Overs faced by team
            overs_bowled: Overs bowled by team
            
        Returns:
            Updated team standing
        """
        # Calculate run rate difference
        run_rate_for = runs_scored / overs_faced if overs_faced > 0 else 0
        run_rate_against = runs_conceded / overs_bowled if overs_bowled > 0 else 0
        nrr_delta = run_rate_for - run_rate_against

        query = """
            UPDATE team_standings
            SET matches_played = matches_played + 1,
                wins = wins + $3,
                losses = losses + $4,
                points = points + $5,
                net_run_rate = (net_run_rate * matches_played + $6) / (matches_played + 1),
                updated_at = CURRENT_TIMESTAMP
            WHERE team_name = $1 AND season = $2
            RETURNING *
        """
        wins_delta = 1 if won else 0
        losses_delta = 0 if won else 1
        points_delta = 2 if won else 0

        return await self.db.fetch_one(
            query, team_name, season, wins_delta, losses_delta, points_delta, nrr_delta
        )


class AchievementRepository(BaseRepository[Achievement]):
    """Repository for Achievement operations"""

    def __init__(self, db: DatabaseManager):
        super().__init__(db, "achievements")

    async def find_by_user(self, user_id: UUID) -> List[Dict]:
        """Find achievements by user"""
        query = """
            SELECT * FROM achievements
            WHERE user_id = $1
            ORDER BY earned_at DESC
        """
        return await self.db.fetch_all(query, str(user_id))

    async def has_achievement(
        self, user_id: UUID, badge_type: str
    ) -> bool:
        """Check if user has a specific achievement"""
        query = """
            SELECT COUNT(*) as count FROM achievements
            WHERE user_id = $1 AND badge_type = $2
        """
        result = await self.db.fetch_one(query, str(user_id), badge_type)
        return result.get("count", 0) > 0 if result else False
