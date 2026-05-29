"""Property tests for Achievement, Profile, and Poll features."""

import pytest
from hypothesis import given, settings, strategies as st
from uuid import uuid4
from datetime import datetime, timezone

from backend.services.achievement_service import AchievementService
from backend.services.user_service import UserService
from backend.services.poll_service import PollService
from backend.services.websocket_manager import WebSocketManager
from backend.cache import MemoryCache


class FakeRepo:
    def __init__(self, data=None):
        self.data = data or []
        
    async def find_by_user(self, user_id, match_type=None):
        return [d for d in self.data if str(d.get("user_id")) == str(user_id)]
        
    async def has_achievement(self, user_id, badge_type):
        return any(d.get("badge_type") == badge_type and str(d.get("user_id")) == str(user_id) for d in self.data)
        
    async def create(self, data):
        self.data.append(data)
        return data

    async def find_by_id(self, id_val, col):
        for d in self.data:
            if str(d.get(col)) == str(id_val):
                return d
        return None


# Feature: ipl-live-score-integration, Property 18: Achievement badge awarding
@pytest.mark.asyncio
async def test_achievement_badge_awarding():
    """
    **Validates: Requirements 5.6**
    
    Property: Users receive specific badges when meeting criteria (predictions, streaks).
    """
    user_id = uuid4()
    
    # 1. 10 Correct predictions badge
    preds_repo = FakeRepo([{"user_id": str(user_id), "is_correct": True}] * 10)
    achieve_repo = FakeRepo([])
    
    service = AchievementService(achieve_repo, preds_repo)
    
    # Check 10 correct
    awarded = await service.check_and_award_achievements(user_id, current_streak=0)
    assert len(awarded) > 0
    assert any(a.badge_type == "10_correct" for a in awarded)
    
    # Check 5 Streak
    preds_repo.data = [{"user_id": str(user_id), "is_correct": True}] * 5
    awarded_streak = await service.check_and_award_achievements(user_id, current_streak=5)
    assert any(a.badge_type == "5_streak" for a in awarded_streak)


# Feature: ipl-live-score-integration, Property 19: Profile display completeness
@pytest.mark.asyncio
async def test_profile_display_completeness():
    """
    **Validates: Requirements 5.7**
    
    Property: User profile accurately aggregates basic info, stats, and achievements.
    """
    user_id = uuid4()
    user_repo = FakeRepo([{
        "user_id": str(user_id),
        "username": "test_user",
        "email": "test@example.com",
        "total_xp": 100,
        "created_at": datetime.now(timezone.utc)
    }])
    
    achieve_repo = FakeRepo([{
        "achievement_id": str(uuid4()),
        "user_id": str(user_id),
        "badge_type": "5_streak",
        "badge_name": "5 Streak",
        "earned_at": datetime.now(timezone.utc)
    }])
    
    pred_repo = FakeRepo([
        {"user_id": str(user_id), "is_correct": True},
        {"user_id": str(user_id), "is_correct": False}
    ])
    
    service = UserService(user_repo, achieve_repo, pred_repo)
    
    profile = await service.get_user_profile(user_id)
    
    assert profile is not None
    assert profile["user"]["username"] == "test_user"
    assert profile["stats"]["total_predictions"] == 2
    assert profile["stats"]["correct_predictions"] == 1
    assert profile["stats"]["accuracy"] == 50.0
    assert len(profile["achievements"]) == 1
    assert profile["achievements"][0]["badge_type"] == "5_streak"


# Test Poll Service functionality
@pytest.mark.asyncio
async def test_poll_service_operations():
    """
    **Validates: Requirements 5.5**
    """
    ws = WebSocketManager()
    service = PollService(ws, MemoryCache())
    
    match_id = "test_match"
    poll = await service.create_poll(match_id, "Who wins?", ["A", "B"])
    
    assert poll.question == "Who wins?"
    
    active = await service.get_active_poll(match_id)
    assert active is not None
    assert active.poll_id == poll.poll_id
    
    user1 = uuid4()
    results = await service.record_response(poll.poll_id, user1, "A")
    assert results is not None
    assert results["A"] == 1
    assert results["B"] == 0
    
    user2 = uuid4()
    results = await service.record_response(poll.poll_id, user2, "B")
    assert results["A"] == 1
    assert results["B"] == 1
    
    # Change vote (user1 changes to B)
    results = await service.record_response(poll.poll_id, user1, "B")
    assert results["A"] == 0
    assert results["B"] == 2
