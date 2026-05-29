# Database Module

This module provides database schema, models, and data access layer for the IPL Live Score Integration.

## Structure

```
database/
├── __init__.py              # Package exports
├── connection.py            # Database connection manager
├── models.py                # Pydantic data models
├── repository.py            # Repository pattern implementation
├── migrations/              # Database migration scripts
│   ├── __init__.py         # Migration runner
│   ├── 001_initial_schema.sql           # SQLite schema
│   └── 001_initial_schema_postgresql.sql # PostgreSQL schema
├── test_setup.py            # Database setup test script
└── README.md                # This file
```

## Features

### Database Connection Manager

The `DatabaseManager` class supports both SQLite and PostgreSQL:

- **SQLite**: For development and testing
- **PostgreSQL**: For production deployment
- Connection pooling for PostgreSQL
- Transaction support with ACID guarantees
- Automatic connection management

### Data Models

All data structures are defined as Pydantic models:

- `User`: User profiles with XP tracking
- `Prediction`: User predictions with evaluation results
- `MatchHistory`: Historical match data
- `PlayerStats`: Player performance statistics
- `TeamStanding`: Team standings with points and NRR
- `Achievement`: User achievement badges
- `LiveMatch`: Real-time match data
- `BallEvent`: Ball-by-ball events
- `ChatMessage`: Chat messages
- `Reaction`: User reactions to events

### Repository Pattern

Base repository with common CRUD operations:

- `UserRepository`: User management
- `PredictionRepository`: Prediction tracking with streak calculation
- `MatchHistoryRepository`: Match history queries
- `PlayerStatsRepository`: Player statistics aggregation
- `TeamStandingRepository`: Team standings with NRR calculation
- `AchievementRepository`: Achievement management

## Usage

### Initialize Database

```python
from database import DatabaseManager, DatabaseType
from database.migrations import run_migrations

# Create database manager
db = DatabaseManager(db_type=DatabaseType.SQLITE)
await db.connect()

# Run migrations
await run_migrations(db)
```

### Use Repositories

```python
from database.repository import UserRepository, PredictionRepository

# Create repositories
user_repo = UserRepository(db)
prediction_repo = PredictionRepository(db)

# Create a user
user_data = {
    "user_id": str(uuid4()),
    "username": "cricket_fan",
    "email": "fan@example.com",
    "total_xp": 0,
}
user = await user_repo.create(user_data)

# Find user by username
user = await user_repo.find_by_username("cricket_fan")

# Update user XP
await user_repo.update_xp(user["user_id"], 10)
```

### Transactions

```python
# Use transaction for atomic operations
async with db.transaction() as conn:
    # All operations here are atomic
    await user_repo.update_xp(user_id, 10)
    await prediction_repo.create(prediction_data)
    # If any operation fails, all are rolled back
```

## Configuration

Set environment variables to configure the database:

```bash
# Database type (sqlite or postgresql)
DATABASE_TYPE=sqlite

# SQLite database URL
SQLITE_DATABASE_URL=sqlite:///./ipl_pulse.db

# PostgreSQL database URL
DATABASE_URL=postgresql://user:password@localhost:5432/ipl_pulse
```

## Testing

Run the test script to verify database setup:

```bash
cd backend
python -m database.test_setup
```

## Migration Scripts

### SQLite Schema (`001_initial_schema.sql`)

- Uses TEXT for UUIDs (stored as strings)
- Compatible with SQLite 3.x
- Includes all necessary indexes

### PostgreSQL Schema (`001_initial_schema_postgresql.sql`)

- Uses native UUID type with `uuid-ossp` extension
- Optimized for PostgreSQL 12+
- Includes all necessary indexes

## Requirements

The following packages are required:

- `asyncpg>=0.29.0` - PostgreSQL async driver
- `aiosqlite>=0.20.0` - SQLite async driver
- `pydantic>=2.0.0` - Data validation and models

## Design Decisions

1. **Repository Pattern**: Abstracts database operations for cleaner code and easier testing
2. **Dual Database Support**: SQLite for development, PostgreSQL for production
3. **Transaction Support**: Ensures data integrity with ACID guarantees
4. **Pydantic Models**: Type-safe data validation and serialization
5. **Async/Await**: Non-blocking database operations for better performance
6. **Connection Pooling**: Efficient resource management for PostgreSQL

## Future Enhancements

- [ ] Add database migration versioning
- [ ] Implement database backup utilities
- [ ] Add query result caching
- [ ] Implement soft deletes
- [ ] Add audit logging for data changes
