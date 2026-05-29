"""
Property-based tests for transaction atomicity

Feature: ipl-live-score-integration, Property 24: Transaction atomicity
**Validates: Requirements 8.5**

For any database transaction involving multiple operations, either all operations
should succeed and be committed, or all should fail and be rolled back.
"""
import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.strategies import composite
from datetime import datetime, timezone
import sys
from pathlib import Path
import asyncio
import os
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseManager, DatabaseType
from database.migrations import run_migrations, drop_all_tables
from database.repository import UserRepository, PredictionRepository


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
    if os.path.exists(db_file):
        os.remove(db_file)


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


# ── Property Tests ─────────────────────────────────────────────────


@given(user_data=user_profile_strategy(), prediction_data_gen=st.data())
@settings(max_examples=15, deadline=None)
def test_transaction_commit_atomicity(user_data, prediction_data_gen):
    """
    Feature: ipl-live-score-integration, Property 24: Transaction atomicity
    
    For any transaction with multiple successful operations, all operations
    should be committed together.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            # Generate prediction data
            prediction_data = prediction_data_gen.draw(prediction_strategy(user_data["user_id"]))
            
            # Execute multiple operations in a transaction using direct SQL
            async with db_manager.transaction() as conn:
                # Operation 1: Create user
                if db_manager.db_type == DatabaseType.SQLITE:
                    await conn.execute(
                        """INSERT INTO users (user_id, username, email, password_hash, total_xp, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (user_data["user_id"], user_data["username"], user_data["email"],
                         user_data["password_hash"], user_data["total_xp"], user_data["created_at"].isoformat())
                    )
                    
                    # Operation 2: Create prediction
                    await conn.execute(
                        """INSERT INTO predictions (prediction_id, user_id, match_id, match_type, 
                                                    predicted_outcome, xp_awarded, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (prediction_data["prediction_id"], prediction_data["user_id"], 
                         prediction_data["match_id"], prediction_data["match_type"],
                         prediction_data["predicted_outcome"], prediction_data["xp_awarded"],
                         prediction_data["created_at"].isoformat())
                    )
                
                # Transaction should commit here
            
            # Verify both operations were committed
            retrieved_user = await db_manager.fetch_one(
                "SELECT * FROM users WHERE user_id = $1",
                user_data["user_id"]
            )
            retrieved_prediction = await db_manager.fetch_one(
                "SELECT * FROM predictions WHERE prediction_id = $1",
                prediction_data["prediction_id"]
            )
            
            # Both should exist (atomicity: all committed)
            assert retrieved_user is not None, "User should be committed"
            assert retrieved_prediction is not None, "Prediction should be committed"
            assert retrieved_user["username"] == user_data["username"]
            assert retrieved_prediction["match_id"] == prediction_data["match_id"]
            
        finally:
            # Cleanup - add small delay to release file lock on Windows
            await db_manager.disconnect()
            await asyncio.sleep(0.1)
            try:
                db_file = test_db_path.replace("sqlite:///", "")
                if os.path.exists(db_file):
                    os.remove(db_file)
            except PermissionError:
                # File still locked, skip cleanup
                pass
    
    asyncio.run(run_test())


@given(user_data=user_profile_strategy())
@settings(max_examples=15, deadline=None)
def test_transaction_rollback_atomicity(user_data):
    """
    Feature: ipl-live-score-integration, Property 24: Transaction atomicity
    
    For any transaction that fails, all operations should be rolled back
    and no changes should be persisted.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            # Attempt a transaction that will fail using direct SQL
            try:
                async with db_manager.transaction() as conn:
                    # Operation 1: Insert user (should succeed)
                    if db_manager.db_type == DatabaseType.SQLITE:
                        await conn.execute(
                            """INSERT INTO users (user_id, username, email, password_hash, total_xp, created_at)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (user_data["user_id"], user_data["username"], user_data["email"],
                             user_data["password_hash"], user_data["total_xp"], user_data["created_at"].isoformat())
                        )
                    
                    # Operation 2: Intentionally raise an error
                    raise ValueError("Simulated transaction failure")
                    
            except ValueError:
                # Expected error
                pass
            
            # Verify the user was NOT committed (rolled back)
            retrieved_user = await db_manager.fetch_one(
                "SELECT * FROM users WHERE user_id = $1",
                user_data["user_id"]
            )
            
            # Should be None (atomicity: all rolled back)
            assert retrieved_user is None, "User should be rolled back on transaction failure"
            
        finally:
            # Cleanup - add small delay to release file lock on Windows
            await db_manager.disconnect()
            await asyncio.sleep(0.1)
            try:
                db_file = test_db_path.replace("sqlite:///", "")
                if os.path.exists(db_file):
                    os.remove(db_file)
            except PermissionError:
                # File still locked, skip cleanup
                pass
    
    asyncio.run(run_test())


@given(user_data=user_profile_strategy(), xp_delta=st.integers(min_value=1, max_value=1000))
@settings(max_examples=15, deadline=None)
def test_transaction_isolation(user_data, xp_delta):
    """
    Feature: ipl-live-score-integration, Property 24: Transaction atomicity
    
    For any transaction, operations should be isolated and either all succeed
    or all fail together, maintaining data consistency.
    """
    async def run_test():
        # Create database
        db_manager, test_db_path = await create_test_db()
        
        try:
            # Create initial user using direct SQL
            await db_manager.execute(
                """INSERT INTO users (user_id, username, email, password_hash, total_xp, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                user_data["user_id"], user_data["username"], user_data["email"],
                user_data["password_hash"], user_data["total_xp"], user_data["created_at"]
            )
            
            initial_xp = user_data["total_xp"]
            
            # Perform XP update in a transaction
            async with db_manager.transaction() as conn:
                # Update XP
                if db_manager.db_type == DatabaseType.SQLITE:
                    await conn.execute(
                        "UPDATE users SET total_xp = total_xp + ? WHERE user_id = ?",
                        (xp_delta, user_data["user_id"])
                    )
            
            # Verify update persisted after transaction commit
            final_user = await db_manager.fetch_one(
                "SELECT * FROM users WHERE user_id = $1",
                user_data["user_id"]
            )
            assert final_user["total_xp"] == initial_xp + xp_delta, \
                "XP update should persist after transaction commit"
            
        finally:
            # Cleanup - add small delay to release file lock on Windows
            await db_manager.disconnect()
            await asyncio.sleep(0.1)
            try:
                db_file = test_db_path.replace("sqlite:///", "")
                if os.path.exists(db_file):
                    os.remove(db_file)
            except PermissionError:
                # File still locked, skip cleanup
                pass
    
    asyncio.run(run_test())
