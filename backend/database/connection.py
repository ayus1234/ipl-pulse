"""
Database connection manager supporting both SQLite and PostgreSQL
"""
import os
import re
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, datetime
import asyncpg
import aiosqlite
from enum import Enum


class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class DatabaseManager:
    """
    Database connection manager that supports both SQLite and PostgreSQL.
    Provides connection pooling and transaction support.
    """

    def __init__(
        self,
        db_type: DatabaseType = DatabaseType.SQLITE,
        database_url: Optional[str] = None,
    ):
        """
        Initialize database manager.

        Args:
            db_type: Type of database (sqlite or postgresql)
            database_url: Connection URL for the database
        """
        # If db_type looks like a connection string, shift it to database_url
        if isinstance(db_type, str) and not isinstance(db_type, DatabaseType) and (db_type.startswith("sqlite") or db_type.startswith("postgres") or "://" in db_type):
            database_url = db_type
            if "postgres" in db_type:
                db_type = DatabaseType.POSTGRESQL
            else:
                db_type = DatabaseType.SQLITE

        self.db_type = db_type
        self.database_url = database_url or self._get_default_url()
        self.pool: Optional[asyncpg.Pool] = None
        self._sqlite_connection: Optional[aiosqlite.Connection] = None

    def _get_default_url(self) -> str:
        """Get default database URL based on environment"""
        if self.db_type == DatabaseType.SQLITE:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_db = os.path.join(base_dir, "ipl_pulse.db")
            default_db_url = default_db.replace("\\", "/")
            return os.getenv("SQLITE_DATABASE_URL", f"sqlite:///{default_db_url}")
        else:
            return os.getenv(
                "DATABASE_URL",
                "postgresql://user:password@localhost:5432/ipl_pulse",
            )

    async def connect(self):
        """Establish database connection"""
        if self.db_type == DatabaseType.POSTGRESQL:
            # Extract connection parameters from URL
            url = self.database_url.replace("postgresql://", "")
            self.pool = await asyncpg.create_pool(
                dsn=f"postgresql://{url}",
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
        else:
            # SQLite connection
            db_path = self.database_url
            for prefix in ["sqlite+aiosqlite:///", "sqlite:///"]:
                if db_path.startswith(prefix):
                    db_path = db_path[len(prefix):]
                    break
            self._sqlite_connection = await aiosqlite.connect(db_path)
            # Enable foreign keys for SQLite
            await self._sqlite_connection.execute("PRAGMA foreign_keys = ON")
            await self._sqlite_connection.commit()

    def _prepare_sqlite_query(self, query: str, args: tuple) -> tuple[str, tuple]:
        """
        Convert PostgreSQL-style placeholders to SQLite placeholders.

        Repository queries use asyncpg's $1/$2 syntax. SQLite requires qmark
        placeholders and one bound value per placeholder occurrence.
        """
        placeholder_pattern = re.compile(r"\$(\d+)")
        sqlite_args = []

        def replace_placeholder(match: re.Match) -> str:
            index = int(match.group(1)) - 1
            if index < 0 or index >= len(args):
                raise ValueError(f"Missing value for SQL placeholder {match.group(0)}")
            sqlite_args.append(self._normalize_sqlite_arg(args[index]))
            return "?"

        converted_query = placeholder_pattern.sub(replace_placeholder, query)
        if sqlite_args:
            return converted_query, tuple(sqlite_args)
        return query, tuple(self._normalize_sqlite_arg(arg) for arg in args)

    def _normalize_sqlite_arg(self, value):
        """Convert values SQLite cannot reliably bind into stable primitives."""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value

    def _is_write_query(self, query: str) -> bool:
        first_word = query.strip().split(maxsplit=1)[0].upper()
        return first_word in {"INSERT", "UPDATE", "DELETE", "REPLACE"}

    async def disconnect(self):
        """Close database connection"""
        if self.db_type == DatabaseType.POSTGRESQL and self.pool:
            await self.pool.close()
            self.pool = None
        elif self._sqlite_connection:
            await self._sqlite_connection.close()
            self._sqlite_connection = None

    @asynccontextmanager
    async def get_connection(self):
        """
        Get a database connection from the pool.
        
        Yields:
            Database connection (asyncpg.Connection or aiosqlite.Connection)
        """
        if self.db_type == DatabaseType.POSTGRESQL:
            if not self.pool:
                raise RuntimeError("Database pool not initialized. Call connect() first.")
            async with self.pool.acquire() as connection:
                yield connection
        else:
            if not self._sqlite_connection:
                raise RuntimeError("Database connection not initialized. Call connect() first.")
            yield self._sqlite_connection

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.
        Ensures atomicity - all operations succeed or all fail.
        
        Yields:
            Database connection within a transaction
        """
        async with self.get_connection() as conn:
            if self.db_type == DatabaseType.POSTGRESQL:
                async with conn.transaction():
                    yield conn
            else:
                # SQLite transaction
                try:
                    await conn.execute("BEGIN")
                    yield conn
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise

    async def execute(self, query: str, *args):
        """
        Execute a query without returning results.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
        """
        async with self.get_connection() as conn:
            if self.db_type == DatabaseType.POSTGRESQL:
                await conn.execute(query, *args)
            else:
                query, args = self._prepare_sqlite_query(query, args)
                await conn.execute(query, args)
                await conn.commit()

    async def fetch_one(self, query: str, *args):
        """
        Fetch a single row from the database.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            
        Returns:
            Single row as a dict or None
        """
        async with self.get_connection() as conn:
            if self.db_type == DatabaseType.POSTGRESQL:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
            else:
                query, args = self._prepare_sqlite_query(query, args)
                async with conn.execute(query, args) as cursor:
                    row = await cursor.fetchone()
                    if self._is_write_query(query):
                        await conn.commit()
                    if row:
                        columns = [desc[0] for desc in cursor.description]
                        return dict(zip(columns, row))
                    return None

    async def fetch_all(self, query: str, *args):
        """
        Fetch all rows from the database.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            
        Returns:
            List of rows as dicts
        """
        async with self.get_connection() as conn:
            if self.db_type == DatabaseType.POSTGRESQL:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
            else:
                query, args = self._prepare_sqlite_query(query, args)
                async with conn.execute(query, args) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        # Determine database type from environment
        db_type_str = os.getenv("DATABASE_TYPE", "sqlite").lower()
        db_type = DatabaseType.SQLITE if db_type_str == "sqlite" else DatabaseType.POSTGRESQL
        _db_manager = DatabaseManager(db_type=db_type)
    return _db_manager


async def init_db():
    """Initialize database connection"""
    db = get_db()
    await db.connect()


async def close_db():
    """Close database connection"""
    db = get_db()
    await db.disconnect()
