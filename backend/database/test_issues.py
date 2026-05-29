"""
Test script to verify the specific issues mentioned are fixed
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseManager, DatabaseType
from database.migrations import run_migrations, drop_all_tables
from database.repository import UserRepository, PredictionRepository
from uuid import uuid4
from datetime import datetime, timezone


async def test_cascade_issue():
    """Test that DROP TABLE works without CASCADE errors in SQLite"""
    print("\n=== Testing CASCADE Issue ===")
    db = DatabaseManager(db_type=DatabaseType.SQLITE, database_url="sqlite:///./test_cascade.db")
    try:
        await db.connect()
        print("[OK] Database connected")
        
        # Run migrations first
        await run_migrations(db)
        print("[OK] Migrations completed")
        
        # Try to drop all tables (this should not fail with CASCADE error)
        await drop_all_tables(db)
        print("[OK] Dropped all tables without CASCADE error")
        
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        raise
    finally:
        await db.disconnect()
        print("[OK] Database disconnected")


async def test_parameter_binding():
    """Test that parameter binding works correctly with SQLite"""
    print("\n=== Testing Parameter Binding Issue ===")
    db = DatabaseManager(db_type=DatabaseType.SQLITE, database_url="sqlite:///./test_params.db")
    try:
        await db.connect()
        print("[OK] Database connected")
        
        # Drop and recreate tables
        await drop_all_tables(db)
        await run_migrations(db)
        print("[OK] Database setup complete")
        
        # Test repository operations that use $1, $2 placeholders
        user_repo = UserRepository(db)
        
        # Create a user (uses $1, $2, etc. placeholders)
        user_data = {
            "user_id": str(uuid4()),
            "username": "test_param_user",
            "email": "param@example.com",
            "total_xp": 0,
            "created_at": datetime.now(timezone.utc),
        }
        user = await user_repo.create(user_data)
        print(f"[OK] Created user with parameter binding: {user['username']}")
        
        # Find by username (uses $1 placeholder)
        found_user = await user_repo.find_by_username("test_param_user")
        assert found_user is not None
        print("[OK] Found user by username with parameter binding")
        
        # Update XP (uses $1, $2 placeholders)
        updated_user = await user_repo.update_xp(user["user_id"], 25)
        assert updated_user["total_xp"] == 25
        print("[OK] Updated user XP with parameter binding")
        
        # Test prediction repository with multiple parameters
        prediction_repo = PredictionRepository(db)
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
        print(f"[OK] Created prediction with parameter binding: {prediction['predicted_outcome']}")
        
        # Find by user (uses $1 placeholder)
        user_predictions = await prediction_repo.find_by_user(user["user_id"])
        assert len(user_predictions) == 1
        print("[OK] Found predictions by user with parameter binding")
        
        # Find by user and match type (uses $1, $2 placeholders)
        filtered_predictions = await prediction_repo.find_by_user(user["user_id"], "live")
        assert len(filtered_predictions) == 1
        print("[OK] Found predictions with multiple parameters")
        
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await db.disconnect()
        print("[OK] Database disconnected")


async def main():
    """Run all tests"""
    print("Testing database issues...")
    
    try:
        await test_cascade_issue()
        await test_parameter_binding()
        print("\n[SUCCESS] All issue tests passed!")
    except Exception as e:
        print(f"\n[FAILURE] Tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
