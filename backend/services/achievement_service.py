"""Service for handling user achievements and badges."""

from typing import List, Optional, Dict
from uuid import UUID

try:
    from backend.database.models import Achievement
    from backend.database.repository import AchievementRepository, PredictionRepository
except ModuleNotFoundError:
    from database.models import Achievement
    from database.repository import AchievementRepository, PredictionRepository


class AchievementService:
    """Handles logic for awarding and retrieving user achievements."""

    # Badge definitions (type -> name/description)
    BADGES = {
        "first_prediction": "First Prediction! 🔮",
        "10_correct": "10 Correct Predictions 🎯",
        "50_correct": "50 Correct Predictions 🏆",
        "100_predictions": "Century of Predictions 💯",
        "5_streak": "On Fire! (5 Streak) 🔥",
        "10_streak": "Unstoppable! (10 Streak) ⚡",
    }

    def __init__(
        self,
        achievement_repo: AchievementRepository,
        prediction_repo: PredictionRepository
    ):
        self.achievement_repo = achievement_repo
        self.prediction_repo = prediction_repo

    async def get_user_achievements(self, user_id: UUID) -> List[Achievement]:
        """Get all achievements for a user."""
        achievements_dict = await self.achievement_repo.find_by_user(user_id)
        return [Achievement.model_validate(a) for a in achievements_dict]

    async def check_and_award_achievements(self, user_id: UUID, current_streak: int = 0) -> List[Achievement]:
        """
        Check user stats and award new achievements if criteria met.
        Should be called after a prediction is evaluated.
        """
        awarded = []
        
        # We need user prediction stats
        preds = await self.prediction_repo.find_by_user(user_id)
        total_preds = len(preds)
        correct_preds = sum(1 for p in preds if p.get("is_correct"))

        # Check First Prediction
        if total_preds >= 1 and not await self.achievement_repo.has_achievement(user_id, "first_prediction"):
            awarded.append(await self._award(user_id, "first_prediction"))

        # Check 100 predictions
        if total_preds >= 100 and not await self.achievement_repo.has_achievement(user_id, "100_predictions"):
            awarded.append(await self._award(user_id, "100_predictions"))

        # Check Correct Predictions milestones
        if correct_preds >= 10 and not await self.achievement_repo.has_achievement(user_id, "10_correct"):
            awarded.append(await self._award(user_id, "10_correct"))
            
        if correct_preds >= 50 and not await self.achievement_repo.has_achievement(user_id, "50_correct"):
            awarded.append(await self._award(user_id, "50_correct"))

        # Check Streaks
        if current_streak >= 5 and not await self.achievement_repo.has_achievement(user_id, "5_streak"):
            awarded.append(await self._award(user_id, "5_streak"))
            
        if current_streak >= 10 and not await self.achievement_repo.has_achievement(user_id, "10_streak"):
            awarded.append(await self._award(user_id, "10_streak"))

        return awarded

    async def _award(self, user_id: UUID, badge_type: str) -> Achievement:
        """Create and save an achievement."""
        achievement = Achievement(
            user_id=user_id,
            badge_type=badge_type,
            badge_name=self.BADGES.get(badge_type, "Unknown Badge")
        )
        saved = await self.achievement_repo.create(achievement.model_dump(mode="json"))
        return Achievement.model_validate(saved)
