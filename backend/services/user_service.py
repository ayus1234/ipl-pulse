"""Service for user profiles and aggregation."""

from typing import Dict, Any, Optional
from uuid import UUID

try:
    from backend.database.models import User
    from backend.database.repository import UserRepository, AchievementRepository, PredictionRepository
except ModuleNotFoundError:
    from database.models import User
    from database.repository import UserRepository, AchievementRepository, PredictionRepository


class UserService:
    """Handles user profile retrieval and aggregation."""

    def __init__(
        self,
        user_repo: UserRepository,
        achievement_repo: AchievementRepository,
        prediction_repo: PredictionRepository
    ):
        self.user_repo = user_repo
        self.achievement_repo = achievement_repo
        self.prediction_repo = prediction_repo

    async def get_user_profile(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Aggregate user statistics, badges, and prediction history.
        Returns a rich profile dict suitable for JSON serialization.
        """
        user_dict = await self.user_repo.find_by_id(str(user_id), "user_id")
        if not user_dict:
            return None
            
        user = User.model_validate(user_dict)
        
        # Get achievements
        achievements_dict = await self.achievement_repo.find_by_user(user_id)
        
        # Get predictions to calculate stats
        preds = await self.prediction_repo.find_by_user(user_id)
        total_preds = len(preds)
        correct_preds = sum(1 for p in preds if p.get("is_correct"))
        accuracy = (correct_preds / total_preds * 100) if total_preds > 0 else 0.0
        
        # We can also fetch prediction history, limit to recent 10 for profile
        recent_preds = preds[:10] if preds else []
        
        # Calculate rank dynamically if needed, but for now just use total_xp
        
        return {
            "user": user.model_dump(mode="json"),
            "stats": {
                "total_predictions": total_preds,
                "correct_predictions": correct_preds,
                "accuracy": round(accuracy, 2)
            },
            "achievements": [a for a in achievements_dict],
            "recent_predictions": [p for p in recent_preds]
        }
