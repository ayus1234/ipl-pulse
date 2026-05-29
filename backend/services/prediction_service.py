"""Service for handling match predictions and leaderboards."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from uuid import UUID

try:
    from backend.database.models import Prediction, MatchType, PredictionResult, LeaderboardEntry
    from backend.database.repository import PredictionRepository, UserRepository
except ModuleNotFoundError:
    from database.models import Prediction, MatchType, PredictionResult, LeaderboardEntry
    from database.repository import PredictionRepository, UserRepository


class PredictionService:
    """Handles predictions, evaluation, and leaderboard calculations."""

    def __init__(
        self,
        prediction_repo: PredictionRepository,
        user_repo: UserRepository
    ):
        self.prediction_repo = prediction_repo
        self.user_repo = user_repo
        # In-memory store for active predictions (not yet evaluated)
        self.active_predictions: Dict[str, Dict[str, Any]] = {}
        # In-memory leaderboard for live matches to avoid heavy DB queries constantly
        self.live_leaderboard: Dict[str, LeaderboardEntry] = {}

    def calculate_streak_bonus(self, streak: int) -> int:
        """Calculate XP multiplier based on streak."""
        if streak >= 5:
            return 3  # 3x bonus
        elif streak >= 3:
            return 2  # 2x bonus
        return 1  # 1x bonus (no multiplier)

    async def create_prediction(
        self,
        user_id: UUID,
        match_id: str,
        match_type: str,
        predicted_outcome: str
    ) -> Prediction:
        """Create a new prediction and lock it."""
        # Create prediction object
        prediction = Prediction(
            user_id=user_id,
            match_id=match_id,
            match_type=MatchType(match_type),
            predicted_outcome=predicted_outcome
        )
        
        # Save to DB
        saved_data = await self.prediction_repo.create(prediction.model_dump(mode="json"))
        saved_prediction = Prediction.model_validate(saved_data)
        
        # Add to active predictions tracking
        key = f"{match_id}_{user_id}"
        self.active_predictions[key] = {
            "prediction_id": saved_prediction.prediction_id,
            "predicted_outcome": predicted_outcome,
            "match_type": match_type
        }
        
        return saved_prediction

    async def evaluate_prediction(
        self,
        prediction_id: UUID,
        actual_outcome: str,
        base_xp: int = 10
    ) -> PredictionResult:
        """Evaluate a specific prediction against the actual outcome."""
        pred_dict = await self.prediction_repo.find_by_id(str(prediction_id), "prediction_id")
        if not pred_dict:
            raise ValueError(f"Prediction {prediction_id} not found")
            
        prediction = Prediction.model_validate(pred_dict)
        is_correct = (prediction.predicted_outcome == actual_outcome)
        
        # Calculate streak and XP
        streak = await self.prediction_repo.get_user_streak(prediction.user_id, prediction.match_type.value)
        streak = streak + 1 if is_correct else 0
        
        multiplier = self.calculate_streak_bonus(streak)
        xp_awarded = base_xp * multiplier if is_correct else 0
        streak_bonus = (xp_awarded - base_xp) if is_correct and multiplier > 1 else 0
        
        # Update prediction
        update_data = {
            "actual_outcome": actual_outcome,
            "is_correct": is_correct,
            "xp_awarded": xp_awarded,
            "evaluated_at": datetime.now(timezone.utc)
        }
        
        await self.prediction_repo.update(str(prediction.prediction_id), update_data, "prediction_id")
        
        if xp_awarded > 0:
            await self.user_repo.update_xp(prediction.user_id, xp_awarded)
            
        return PredictionResult(
            prediction_id=prediction.prediction_id,
            is_correct=is_correct,
            xp_awarded=xp_awarded,
            streak_bonus=streak_bonus
        )

    async def get_user_predictions(
        self,
        user_id: UUID,
        match_type: Optional[str] = None
    ) -> List[Prediction]:
        """Get prediction history for a user."""
        preds = await self.prediction_repo.find_by_user(user_id, match_type)
        return [Prediction.model_validate(p) for p in preds]

    async def get_leaderboard(
        self,
        match_type: str = "live",
        limit: int = 20
    ) -> List[LeaderboardEntry]:
        """Get top users by XP for a specific match type."""
        # We query users table ordered by total_xp
        query = "SELECT * FROM users ORDER BY total_xp DESC LIMIT $1"
        users = await self.user_repo.db.fetch_all(query, limit)
        
        leaderboard = []
        for i, user in enumerate(users):
            # In a real app we'd aggregate predictions to get accuracy/total
            # Here we do a simple query or mock for accuracy
            query_preds = "SELECT COUNT(*) as total, SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct FROM predictions WHERE user_id = $1"
            stats = await self.prediction_repo.db.fetch_one(query_preds, user["user_id"])
            total = stats.get("total", 0) if stats else 0
            correct = stats.get("correct", 0) if stats else 0
            accuracy = (correct / total * 100) if total > 0 else 0.0
            
            leaderboard.append(LeaderboardEntry(
                user_id=UUID(user["user_id"]),
                username=user["username"],
                total_xp=user["total_xp"],
                correct_predictions=correct,
                total_predictions=total,
                accuracy=accuracy,
                rank=i + 1
            ))
            
        return leaderboard
