"""
Pydantic models for all data structures
"""
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class MatchType(str, Enum):
    """Type of match"""
    LIVE = "live"
    SIMULATED = "simulated"


class MatchStatus(str, Enum):
    """Status of a match"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ── User Models ────────────────────────────────────────────────────


class User(BaseModel):
    """User profile model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "username": "cricket_fan_123",
            "email": "fan@example.com",
            "total_xp": 1500,
            "created_at": "2024-01-15T10:30:00Z",
        }
    })

    user_id: UUID = Field(default_factory=uuid4)
    username: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    password_hash: Optional[str] = Field(None, max_length=255)
    total_xp: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)


# ── Prediction Models ──────────────────────────────────────────────


class Prediction(BaseModel):
    """User prediction model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "prediction_id": "123e4567-e89b-12d3-a456-426614174001",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "match_id": "ipl_2024_match_001",
            "match_type": "live",
            "predicted_outcome": "6",
            "actual_outcome": "6",
            "is_correct": True,
            "xp_awarded": 10,
            "created_at": "2024-01-15T14:30:00Z",
            "evaluated_at": "2024-01-15T14:30:15Z",
        }
    })

    prediction_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    match_id: str = Field(..., max_length=100)
    match_type: MatchType
    predicted_outcome: str = Field(..., max_length=50)
    actual_outcome: Optional[str] = Field(None, max_length=50)
    is_correct: Optional[bool] = None
    xp_awarded: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    evaluated_at: Optional[datetime] = None


# ── Match Models ───────────────────────────────────────────────────


class LiveMatch(BaseModel):
    """Live match data model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "match_id": "ipl_2024_match_001",
            "team1": "CSK",
            "team2": "MI",
            "team1_score": "185/6",
            "team2_score": "120/3",
            "overs": 15.4,
            "status": "live",
            "current_batsmen": ["MS Dhoni", "Ravindra Jadeja"],
            "current_bowler": "Jasprit Bumrah",
            "last_updated": "2024-01-15T14:30:00Z",
        }
    })

    match_id: str
    team1: str
    team2: str
    team1_score: str  # e.g., "185/6"
    team2_score: str
    overs: float
    status: MatchStatus
    current_batsmen: List[str]
    current_bowler: str
    last_updated: datetime


class BallEvent(BaseModel):
    """Ball-by-ball event model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ball_id": "match_001_ball_094",
            "match_id": "ipl_2024_match_001",
            "over": 15.4,
            "batsman": "MS Dhoni",
            "bowler": "Jasprit Bumrah",
            "runs": 6,
            "is_wicket": False,
            "commentary": "MASSIVE! Dhoni sends it into the stands!",
            "timestamp": "2024-01-15T14:30:00Z",
        }
    })

    ball_id: str
    match_id: str
    over: float
    batsman: str
    bowler: str
    runs: int
    is_wicket: bool
    commentary: str
    timestamp: datetime


class MatchHistory(BaseModel):
    """Match history model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "match_id": "ipl_2024_match_001",
            "match_type": "live",
            "team1": "CSK",
            "team2": "MI",
            "winner": "CSK",
            "final_score_team1": "185/6",
            "final_score_team2": "180/8",
            "match_date": "2024-01-15T14:00:00Z",
            "status": "completed",
            "created_at": "2024-01-15T17:00:00Z",
        }
    })

    match_id: str = Field(..., max_length=100)
    match_type: MatchType
    team1: str = Field(..., max_length=100)
    team2: str = Field(..., max_length=100)
    winner: Optional[str] = Field(None, max_length=100)
    final_score_team1: Optional[str] = Field(None, max_length=50)
    final_score_team2: Optional[str] = Field(None, max_length=50)
    match_date: datetime
    status: MatchStatus
    created_at: datetime = Field(default_factory=utc_now)


# ── Statistics Models ──────────────────────────────────────────────


class PlayerStats(BaseModel):
    """Player statistics model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "player_id": "player_dhoni",
            "player_name": "MS Dhoni",
            "team": "CSK",
            "matches_played": 250,
            "runs_scored": 5000,
            "wickets_taken": 0,
            "balls_faced": 3500,
            "balls_bowled": 0,
            "runs_conceded": 0,
            "updated_at": "2024-01-15T17:00:00Z",
        }
    })

    player_id: str = Field(..., max_length=100)
    player_name: str = Field(..., max_length=100)
    team: Optional[str] = Field(None, max_length=100)
    matches_played: int = Field(default=0, ge=0)
    runs_scored: int = Field(default=0, ge=0)
    wickets_taken: int = Field(default=0, ge=0)
    balls_faced: int = Field(default=0, ge=0)
    balls_bowled: int = Field(default=0, ge=0)
    runs_conceded: int = Field(default=0, ge=0)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def strike_rate(self) -> float:
        """Calculate batting strike rate"""
        if self.balls_faced == 0:
            return 0.0
        return (self.runs_scored / self.balls_faced) * 100

    @property
    def economy_rate(self) -> float:
        """Calculate bowling economy rate"""
        if self.balls_bowled == 0:
            return 0.0
        overs = self.balls_bowled / 6
        return self.runs_conceded / overs if overs > 0 else 0.0

    @property
    def average(self) -> float:
        """Calculate batting average"""
        # Simplified: assuming wickets_taken represents times out for batting
        if self.wickets_taken == 0:
            return float(self.runs_scored)
        return self.runs_scored / self.wickets_taken

class TeamStanding(BaseModel):
    """Team standings model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "team_name": "CSK",
            "season": "2024",
            "matches_played": 14,
            "wins": 10,
            "losses": 4,
            "no_result": 0,
            "points": 20,
            "net_run_rate": 0.850,
            "updated_at": "2024-01-15T17:00:00Z",
        }
    })

    team_name: str = Field(..., max_length=100)
    season: str = Field(..., max_length=20)
    matches_played: int = Field(default=0, ge=0)
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    no_result: int = Field(default=0, ge=0)
    points: int = Field(default=0, ge=0)
    net_run_rate: float = Field(default=0.0)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def position(self) -> int:
        """Position in standings (calculated separately in queries)"""
        return 0  # Placeholder, calculated in service layer


# ── Social Models ──────────────────────────────────────────────────


class ChatMessage(BaseModel):
    """Chat message model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message_id": "msg_12345",
            "match_id": "ipl_2024_match_001",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "username": "cricket_fan_123",
            "content": "What a shot by Dhoni!",
            "timestamp": "2024-01-15T14:30:00Z",
        }
    })

    message_id: str
    match_id: str
    user_id: str
    username: str
    content: str = Field(..., max_length=500)
    timestamp: datetime


class Reaction(BaseModel):
    """Reaction to a ball event"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "reaction_id": "react_12345",
            "match_id": "ipl_2024_match_001",
            "ball_id": "match_001_ball_094",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "emoji": "🔥",
            "timestamp": "2024-01-15T14:30:00Z",
        }
    })

    reaction_id: str
    match_id: str
    ball_id: str
    user_id: str
    emoji: str = Field(..., max_length=10)
    timestamp: datetime

class Achievement(BaseModel):
    """User achievement model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "achievement_id": "123e4567-e89b-12d3-a456-426614174002",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "badge_type": "prediction_milestone",
            "badge_name": "10 Correct Predictions",
            "earned_at": "2024-01-15T15:00:00Z",
        }
    })

    achievement_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    badge_type: str = Field(..., max_length=50)
    badge_name: str = Field(..., max_length=100)
    earned_at: datetime = Field(default_factory=utc_now)

# ── Additional Models ──────────────────────────────────────────────


class LeaderboardEntry(BaseModel):
    """Leaderboard entry model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "username": "cricket_fan_123",
            "total_xp": 1500,
            "correct_predictions": 75,
            "total_predictions": 100,
            "accuracy": 75.0,
            "rank": 1,
        }
    })

    user_id: UUID
    username: str
    total_xp: int
    correct_predictions: int
    total_predictions: int
    accuracy: float
    rank: int


class PredictionResult(BaseModel):
    """Result of a prediction evaluation"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "prediction_id": "123e4567-e89b-12d3-a456-426614174001",
            "is_correct": True,
            "xp_awarded": 10,
            "streak_bonus": 6,
        }
    })

    prediction_id: UUID
    is_correct: bool
    xp_awarded: int
    streak_bonus: int = 0


class Poll(BaseModel):
    """Real-time poll model"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "poll_id": "poll_123",
            "match_id": "ipl_2024_match_001",
            "question": "Who will win the match?",
            "options": ["CSK", "MI"],
            "created_at": "2024-01-15T14:30:00Z",
            "active": True
        }
    })

    poll_id: str = Field(default_factory=lambda: str(uuid4()))
    match_id: str
    question: str
    options: List[str]
    created_at: datetime = Field(default_factory=utc_now)
    active: bool = True


class PollResponse(BaseModel):
    """User response to a poll"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "poll_id": "poll_123",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "selected_option": "CSK",
            "timestamp": "2024-01-15T14:30:10Z"
        }
    })

    poll_id: str
    user_id: UUID
    selected_option: str
    timestamp: datetime = Field(default_factory=utc_now)
