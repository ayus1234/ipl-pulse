"""
Property-based tests for database round-trip persistence

Feature: ipl-live-score-integration, Property 5: Data persistence round-trip
**Validates: Requirements 2.2, 8.1, 8.2, 8.3**

For any user profile, prediction, or match data written to the Data_Store,
reading it back should return equivalent data.
"""
import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.strategies import composite
from uuid import UUID
from datetime import datetime, timezone, date
import sys
from pathlib import Path
import asyncio
import os
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseManager, DatabaseType
from database.migrations import run_migrations, drop_all_tables
from database.repository import (
    UserRepository,
    PredictionRepository,
    MatchHistoryRepository,
    PlayerStatsRepository,
    AchievementRepository,
)


# ── Helper Functions ───────────────────────────────────────────────


async def create_test_db():
    """Create a fresh test database"""
    test_db_path = f"sqlite:///./test_db_{os.getpid()}_{random.randint(1000, 9999)}.db"
    db_manager = DatabaseManager(db_type=DatabaseType.SQLITE, database_url=test_db_path)
    
    await db_manager.connect()
    await drop_all_tables(db_manager)
    await run_migrations(db_manager)
    
    return db_manager, test_db_path


async def cleanup_test_db(db_manager, test_db_path):
    """Cleanup test database"""
    await db_manager.disconnect()
    db_file = test_db_path.replace("sqlite:///", "")
    for _ in range(5):
        try:
            if os.path.exists(db_file):
                os.remove(db_file)
            return
        except PermissionError:
            await asyncio.sleep(0.05)


# ── Strategy Generators ────────────────────────────────────────────


@composite
def user_profile_strategy(draw):
    """Generate valid user profile data"""
    return {
        "user_id": str(draw(st.uuids())),
        "username": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        ))),
        "email": draw(st.emails()),
        "password_hash": draw(st.text(min_size=10, max_size=255)),
        "total_xp": draw(st.integers(min_value=0, max_value=1000000)),
        "created_at": datetime.now(timezone.utc),
    }


@composite
def prediction_strategy(draw, user_id):
    """Generate valid prediction data"""
    return {
        "prediction_id": str(draw(st.uuids())),
        "user_id": user_id,
        "match_id": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        ))),
        "match_type": draw(st.sampled_from(["live", "simulated"])),
        "predicted_outcome": draw(st.sampled_from(["0", "1", "2", "3", "4", "6", "wicket", "dot"])),
        "actual_outcome": None,
        "is_correct": None,
        "xp_awarded": draw(st.integers(min_value=0, max_value=100)),
        "created_at": datetime.now(timezone.utc),
        "evaluated_at": None,
    }


@composite
def match_history_strategy(draw):
    """Generate valid match history data"""
    teams = ["CSK", "MI", "RCB", "KKR", "DC", "RR", "PBKS", "SRH", "GT", "LSG"]
    team1 = draw(st.sampled_from(teams))
    team2 = draw(st.sampled_from([t for t in teams if t != team1]))
    
    return {
        "match_id": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        ))),
        "match_type": draw(st.sampled_from(["live", "simulated"])),
        "team1": team1,
        "team2": team2,
        "winner": draw(st.sampled_from([team1, team2, None])),
        "final_score_team1": draw(st.text(min_size=1, max_size=50)),
        "final_score_team2": draw(st.text(min_size=1, max_size=50)),
        "match_date": date.today(),
        "status": draw(st.sampled_from(["scheduled", "live", "completed", "abandoned"])),
        "created_at": datetime.now(timezone.utc),
    }


@composite
def player_stats_strategy(draw):
    """Generate valid player statistics data"""
    return {
        "player_id": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        ))),
        "player_name": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'),
            whitelist_characters=' '
        ))),
        "team": draw(st.sampled_from(["CSK", "MI", "RCB", "KKR", "DC", "RR", "PBKS", "SRH", "GT", "LSG"])),
        "matches_played": draw(st.integers(min_value=0, max_value=500)),
        "runs_scored": draw(st.integers(min_value=0, max_value=10000)),
        "wickets_taken": draw(st.integers(min_value=0, max_value=500)),
        "balls_faced": draw(st.integers(min_value=0, max_value=10000)),
        "balls_bowled": draw(st.integers(min_value=0, max_value=10000)),
        "runs_conceded": draw(st.integers(min_value=0, max_value=10000)),
        "updated_at": datetime.now(timezone.utc),
    }


@composite
def achievement_strategy(draw, user_id):
    """Generate valid achievement data"""
    return {
        "achievement_id": str(draw(st.uuids())),
        "user_id": user_id,
        "badge_type": draw(st.sampled_from([
            "prediction_milestone",
            "accuracy_master",
            "streak_champion",
            "social_butterfly"
        ])),
        "badge_name": draw(st.text(min_size=1, max_size=100)),
        "earned_at": datetime.now(timezone.utc),
    }


# ── Property Tests ─────────────────────────────────────────────────


@given(user_data=user_profile_strategy())
@settings(max_examples=20, deadline=None)
def test_user_profile_round_trip(user_data):
    """
    Feature: ipl-live-score-integration, Property 5: Data persistence round-trip
    
    For any user profile written to the database, reading it back should
    return equivalent data.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            user_repo = UserRepository(db_manager)
            
            # Write user profile to database
            created_user = await user_repo.create(user_data)
            
            # Read it back
            retrieved_user = await user_repo.find_by_id(created_user["user_id"], "user_id")
            
            # Should be equivalent (compare key fields)
            assert retrieved_user is not None
            assert retrieved_user["user_id"] == user_data["user_id"]
            assert retrieved_user["username"] == user_data["username"]
            assert retrieved_user["email"] == user_data["email"]
            assert retrieved_user["total_xp"] == user_data["total_xp"]
        finally:
            # Cleanup
            await cleanup_test_db(db_manager, test_db_path)
    
    asyncio.run(run_test())


@given(user_data=user_profile_strategy(), prediction_data_gen=st.data())
@settings(max_examples=20, deadline=None)
def test_prediction_round_trip(user_data, prediction_data_gen):
    """
    Feature: ipl-live-score-integration, Property 5: Data persistence round-trip
    
    For any prediction written to the database, reading it back should
    return equivalent data.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            user_repo = UserRepository(db_manager)
            prediction_repo = PredictionRepository(db_manager)
            
            # Create user first
            user = await user_repo.create(user_data)
            
            # Generate prediction data using draw
            prediction_data = prediction_data_gen.draw(prediction_strategy(user["user_id"]))
            
            # Write prediction to database
            created_prediction = await prediction_repo.create(prediction_data)
            
            # Read it back
            retrieved_prediction = await prediction_repo.find_by_id(
                created_prediction["prediction_id"],
                "prediction_id"
            )
            
            # Should be equivalent
            assert retrieved_prediction is not None
            assert retrieved_prediction["prediction_id"] == prediction_data["prediction_id"]
            assert retrieved_prediction["user_id"] == prediction_data["user_id"]
            assert retrieved_prediction["match_id"] == prediction_data["match_id"]
            assert retrieved_prediction["match_type"] == prediction_data["match_type"]
            assert retrieved_prediction["predicted_outcome"] == prediction_data["predicted_outcome"]
            assert retrieved_prediction["xp_awarded"] == prediction_data["xp_awarded"]
        finally:
            # Cleanup
            await cleanup_test_db(db_manager, test_db_path)
    
    asyncio.run(run_test())


@given(match_data=match_history_strategy())
@settings(max_examples=20, deadline=None)
def test_match_history_round_trip(match_data):
    """
    Feature: ipl-live-score-integration, Property 5: Data persistence round-trip
    
    For any match history written to the database, reading it back should
    return equivalent data.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            match_repo = MatchHistoryRepository(db_manager)
            
            # Write match history to database
            created_match = await match_repo.create(match_data)
            
            # Read it back
            retrieved_match = await match_repo.find_by_id(created_match["match_id"], "match_id")
            
            # Should be equivalent
            assert retrieved_match is not None
            assert retrieved_match["match_id"] == match_data["match_id"]
            assert retrieved_match["match_type"] == match_data["match_type"]
            assert retrieved_match["team1"] == match_data["team1"]
            assert retrieved_match["team2"] == match_data["team2"]
            assert retrieved_match["status"] == match_data["status"]
        finally:
            # Cleanup
            await cleanup_test_db(db_manager, test_db_path)
    
    asyncio.run(run_test())


@given(player_data=player_stats_strategy())
@settings(max_examples=20, deadline=None)
def test_player_stats_round_trip(player_data):
    """
    Feature: ipl-live-score-integration, Property 5: Data persistence round-trip
    
    For any player statistics written to the database, reading it back should
    return equivalent data.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            player_repo = PlayerStatsRepository(db_manager)
            
            # Write player stats to database
            created_player = await player_repo.create(player_data)
            
            # Read it back
            retrieved_player = await player_repo.find_by_id(created_player["player_id"], "player_id")
            
            # Should be equivalent
            assert retrieved_player is not None
            assert retrieved_player["player_id"] == player_data["player_id"]
            assert retrieved_player["player_name"] == player_data["player_name"]
            assert retrieved_player["team"] == player_data["team"]
            assert retrieved_player["matches_played"] == player_data["matches_played"]
            assert retrieved_player["runs_scored"] == player_data["runs_scored"]
            assert retrieved_player["wickets_taken"] == player_data["wickets_taken"]
        finally:
            # Cleanup
            await cleanup_test_db(db_manager, test_db_path)
    
    asyncio.run(run_test())


@given(user_data=user_profile_strategy(), achievement_data_gen=st.data())
@settings(max_examples=20, deadline=None)
def test_achievement_round_trip(user_data, achievement_data_gen):
    """
    Feature: ipl-live-score-integration, Property 5: Data persistence round-trip
    
    For any achievement written to the database, reading it back should
    return equivalent data.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            user_repo = UserRepository(db_manager)
            achievement_repo = AchievementRepository(db_manager)
            
            # Create user first
            user = await user_repo.create(user_data)
            
            # Generate achievement data using draw
            achievement_data = achievement_data_gen.draw(achievement_strategy(user["user_id"]))
            
            # Write achievement to database
            created_achievement = await achievement_repo.create(achievement_data)
            
            # Read it back
            retrieved_achievement = await achievement_repo.find_by_id(
                created_achievement["achievement_id"],
                "achievement_id"
            )
            
            # Should be equivalent
            assert retrieved_achievement is not None
            assert retrieved_achievement["achievement_id"] == achievement_data["achievement_id"]
            assert retrieved_achievement["user_id"] == achievement_data["user_id"]
            assert retrieved_achievement["badge_type"] == achievement_data["badge_type"]
            assert retrieved_achievement["badge_name"] == achievement_data["badge_name"]
        finally:
            # Cleanup
            await cleanup_test_db(db_manager, test_db_path)
    
    asyncio.run(run_test())
