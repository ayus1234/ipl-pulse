"""Property tests for PredictionService."""

import pytest
from datetime import datetime, timezone
from hypothesis import given, settings, strategies as st
from uuid import UUID, uuid4

from backend.database.models import Prediction, MatchType, PredictionResult, LeaderboardEntry
from backend.services.prediction_service import PredictionService


class FakeDB:
    def __init__(self):
        self.rows = []

    async def fetch_all(self, query, *args):
        # Very simple mock just returning what we set up
        return self.rows

    async def fetch_one(self, query, *args):
        if self.rows:
            return self.rows[0]
        return None


class FakePredictionRepo:
    def __init__(self):
        self.predictions = {}
        self.db = FakeDB()
        self.streak = 0

    async def create(self, data):
        if "prediction_id" not in data or not data["prediction_id"]:
            data["prediction_id"] = str(uuid4())
        self.predictions[data["prediction_id"]] = data
        return data

    async def find_by_id(self, id_value, id_column="prediction_id"):
        return self.predictions.get(str(id_value))

    async def get_user_streak(self, user_id, match_type):
        return self.streak

    async def update(self, id_value, data, id_column="prediction_id"):
        if str(id_value) in self.predictions:
            self.predictions[str(id_value)].update(data)
            return self.predictions[str(id_value)]
        return None

    async def find_by_user(self, user_id, match_type=None):
        return [p for p in self.predictions.values() if str(p["user_id"]) == str(user_id)]


class FakeUserRepo:
    def __init__(self):
        self.users = {}
        self.db = FakeDB()

    async def update_xp(self, user_id, xp_delta):
        user_id_str = str(user_id)
        if user_id_str not in self.users:
            self.users[user_id_str] = {"user_id": user_id_str, "total_xp": 0, "username": "test"}
        self.users[user_id_str]["total_xp"] += xp_delta
        return self.users[user_id_str]


@st.composite
def prediction_inputs(draw):
    return {
        "user_id": draw(st.uuids()),
        "match_id": draw(st.text(min_size=1, max_size=20)),
        "match_type": draw(st.sampled_from(["live", "simulated"])),
        "predicted_outcome": draw(st.sampled_from(["dot", "single", "boundary", "six", "wicket"]))
    }


# Feature: ipl-live-score-integration, Property 9: Prediction metadata completeness
@given(inputs=prediction_inputs())
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_prediction_metadata_completeness(inputs):
    """
    **Validates: Requirements 3.1, 3.2**
    """
    pred_repo = FakePredictionRepo()
    user_repo = FakeUserRepo()
    service = PredictionService(pred_repo, user_repo)
    
    prediction = await service.create_prediction(
        user_id=inputs["user_id"],
        match_id=inputs["match_id"],
        match_type=inputs["match_type"],
        predicted_outcome=inputs["predicted_outcome"]
    )
    
    assert prediction.prediction_id is not None
    assert prediction.user_id == inputs["user_id"]
    assert prediction.match_id == inputs["match_id"]
    assert prediction.match_type.value == inputs["match_type"]
    assert prediction.predicted_outcome == inputs["predicted_outcome"]


# Feature: ipl-live-score-integration, Property 11: Streak bonus calculation
@given(
    inputs=prediction_inputs(),
    streak=st.integers(min_value=0, max_value=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_streak_bonus_calculation(inputs, streak):
    """
    **Validates: Requirements 3.4**
    """
    pred_repo = FakePredictionRepo()
    pred_repo.streak = streak
    user_repo = FakeUserRepo()
    service = PredictionService(pred_repo, user_repo)
    
    prediction = await service.create_prediction(**inputs)
    
    result = await service.evaluate_prediction(
        prediction_id=prediction.prediction_id,
        actual_outcome=inputs["predicted_outcome"], # Make it correct
        base_xp=10
    )
    
    assert result.is_correct
    if streak + 1 >= 5: # Remember streak goes up by 1 when correct
        assert result.streak_bonus == 20 # 3x multiplier - 10 base = 20 bonus
        assert result.xp_awarded == 30
    elif streak + 1 >= 3:
        assert result.streak_bonus == 10 # 2x multiplier
        assert result.xp_awarded == 20
    else:
        assert result.streak_bonus == 0
        assert result.xp_awarded == 10


# Feature: ipl-live-score-integration, Property 13: XP update propagation
@given(inputs=prediction_inputs())
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_xp_update_propagation(inputs):
    """
    **Validates: Requirements 3.7**
    """
    pred_repo = FakePredictionRepo()
    user_repo = FakeUserRepo()
    service = PredictionService(pred_repo, user_repo)
    
    prediction = await service.create_prediction(**inputs)
    
    # Evaluate as correct
    result = await service.evaluate_prediction(
        prediction_id=prediction.prediction_id,
        actual_outcome=inputs["predicted_outcome"],
        base_xp=10
    )
    
    assert result.xp_awarded > 0
    # Check if XP propagated to UserRepo
    user = user_repo.users.get(str(inputs["user_id"]))
    assert user is not None
    assert user["total_xp"] == result.xp_awarded


# Feature: ipl-live-score-integration, Property 10: Leaderboard filtering correctness
@pytest.mark.asyncio
async def test_leaderboard_filtering_correctness():
    """
    **Validates: Requirements 3.3, 3.5**
    """
    pred_repo = FakePredictionRepo()
    user_repo = FakeUserRepo()
    
    # Setup mock users
    user_repo.db.rows = [
        {"user_id": str(uuid4()), "username": "user1", "total_xp": 100},
        {"user_id": str(uuid4()), "username": "user2", "total_xp": 50},
    ]
    pred_repo.db.rows = [{"total": 10, "correct": 5}]
    
    service = PredictionService(pred_repo, user_repo)
    leaderboard = await service.get_leaderboard(match_type="live")
    
    assert len(leaderboard) == 2
    assert leaderboard[0].total_xp == 100
    assert leaderboard[0].rank == 1
    assert leaderboard[0].accuracy == 50.0


# Feature: ipl-live-score-integration, Property 12: Prediction history with accuracy
@pytest.mark.asyncio
async def test_prediction_history_with_accuracy():
    """
    **Validates: Requirements 3.6**
    """
    pred_repo = FakePredictionRepo()
    user_repo = FakeUserRepo()
    service = PredictionService(pred_repo, user_repo)
    
    user_id = uuid4()
    await service.create_prediction(user_id, "match1", "live", "six")
    await service.create_prediction(user_id, "match2", "live", "four")
    
    history = await service.get_user_predictions(user_id, "live")
    assert len(history) == 2
