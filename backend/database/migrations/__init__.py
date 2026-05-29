"""
Database migration utilities
"""
import os
from pathlib import Path
from typing import List
from ..connection import DatabaseManager, DatabaseType


async def run_migrations(db: DatabaseManager):
    """
    Run all database migrations.
    
    Args:
        db: DatabaseManager instance
    """
    migrations_dir = Path(__file__).parent
    
    # Determine which migration file to use
    if db.db_type == DatabaseType.POSTGRESQL:
        migration_file = migrations_dir / "001_initial_schema_postgresql.sql"
    else:
        migration_file = migrations_dir / "001_initial_schema.sql"
    
    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")
    
    # Read and execute migration
    with open(migration_file, "r") as f:
        sql = f.read()
    
    # Split by semicolon and execute each statement
    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    
    for statement in statements:
        if statement:
            try:
                await db.execute(statement)
            except Exception as e:
                print(f"Error executing migration statement: {e}")
                print(f"Statement: {statement[:100]}...")
                raise


async def drop_all_tables(db: DatabaseManager):
    """
    Drop all tables (for testing purposes).
    
    Args:
        db: DatabaseManager instance
    """
    tables = [
        "achievements",
        "predictions",
        "team_standings",
        "player_stats",
        "match_history",
        "users",
    ]
    
    for table in tables:
        try:
            cascade = " CASCADE" if db.db_type == DatabaseType.POSTGRESQL else ""
            await db.execute(f"DROP TABLE IF EXISTS {table}{cascade}")
        except Exception as e:
            print(f"Error dropping table {table}: {e}")
