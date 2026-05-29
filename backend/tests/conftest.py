"""
Pytest configuration and fixtures for database tests
"""
import pytest
import asyncio
import os
from pathlib import Path
import sys

# Make imports work when pytest is run from either the repository root or
# the backend directory.
BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from database.connection import DatabaseManager, DatabaseType
from database.migrations import run_migrations, drop_all_tables


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db(event_loop):
    """
    Provide a clean database for each test.
    Uses SQLite with a temporary database file.
    Returns a coroutine that creates the database.
    """
    async def _create_db():
        # Use a unique database file for each test
        import random
        test_db_path = f"sqlite:///./test_db_{os.getpid()}_{random.randint(1000, 9999)}.db"
        db_manager = DatabaseManager(db_type=DatabaseType.SQLITE, database_url=test_db_path)
        
        await db_manager.connect()
        
        # Drop existing tables and run migrations
        await drop_all_tables(db_manager)
        await run_migrations(db_manager)
        
        return db_manager, test_db_path
    
    return _create_db
