"""
Test script to verify database setup
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseManager, DatabaseType
from database.migrations import run_migrations, drop_all_tables
from database.repository import (
    UserRepository,
    PredictionRepository,
    MatchHistoryRepository,
    PlayerStatsRepository,
    TeamStandingRepository,
    AchievementRepository,
)
from database.models import User, Prediction, MatchType, MatchStatus
from uuid import uuid4
from datetime import datetime, timezone


async def test_database_setup():
    """Test database setup and basic operations"""
    print("Testing database setup...")
    
    # Initialize database manager (SQLite for testing)
    db = DatabaseManager(db_type=DatabaseType.SQLITE, database_url="sqlite:///./test_ipl.db")
    try:
        await db.connect()
        print("[OK] Database connected")
        
        # Drop existing tables
        await drop_all_tables(db)
        print("[OK] Dropped existing tables")
        
        # Run migrations
        await run_migrations(db)
        print("[OK] Migrations completed")
        
        # Test repositories
        user_repo = UserRepository(db)
        prediction_repo = PredictionRepository(db)
        
        # Create a test user
        user_data = {
            "user_id": str(uuid4()),
            "username": "test_user",
            "email": "test@example.com",
            "total_xp": 0,
            "created_at": datetime.now(timezone.utc),
        }
        user = await user_repo.create(user_data)
        print(f"[OK] Created user: {user['username']}")
        
        # Find user by username
        found_user = await user_repo.find_by_username("test_user")
        assert found_user is not None
        assert found_user["username"] == "test_user"
        print("[OK] Found user by username")
        
        # Create a test prediction
        prediction_data = {
            "prediction_id": str(uuid4()),
            "user_id": user["user_id"],
            "match_id": "test_match_001",
            "match_type": "live",
            "predicted_outcome": "6",
            "xp_awarded": 0,
            "created_at": datetime.now(timezone.utc),
        }
        prediction = await prediction_repo.create(prediction_data)
        print(f"[OK] Created prediction: {prediction['predicted_outcome']}")
        
        # Find predictions by user
        user_predictions = await prediction_repo.find_by_user(user["user_id"])
        assert len(user_predictions) == 1
        print("[OK] Found user predictions")
        
        # Update user XP
        updated_user = await user_repo.update_xp(user["user_id"], 10)
        assert updated_user["total_xp"] == 10
        print("[OK] Updated user XP")
        
        # Test transaction
        async with db.transaction() as conn:
            print("[OK] Transaction started")
        print("[OK] Transaction committed")
        
        print("\n[SUCCESS] All database tests passed!")
    finally:
        await db.disconnect()
        print("[OK] Database disconnected")


if __name__ == "__main__":
    asyncio.run(test_database_setup())
