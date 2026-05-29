-- Initial database schema for IPL Live Score Integration
-- Supports both PostgreSQL and SQLite with conditional syntax

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    total_xp INTEGER DEFAULT 0 CHECK (total_xp >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    match_id VARCHAR(100) NOT NULL,
    match_type VARCHAR(20) NOT NULL CHECK (match_type IN ('live', 'simulated')),
    predicted_outcome VARCHAR(50) NOT NULL,
    actual_outcome VARCHAR(50),
    is_correct BOOLEAN,
    xp_awarded INTEGER DEFAULT 0 CHECK (xp_awarded >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_match ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_type ON predictions(match_type);

-- Match history table
CREATE TABLE IF NOT EXISTS match_history (
    match_id VARCHAR(100) PRIMARY KEY,
    match_type VARCHAR(20) NOT NULL CHECK (match_type IN ('live', 'simulated')),
    team1 VARCHAR(100) NOT NULL,
    team2 VARCHAR(100) NOT NULL,
    winner VARCHAR(100),
    final_score_team1 VARCHAR(50),
    final_score_team2 VARCHAR(50),
    match_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('scheduled', 'live', 'completed', 'abandoned')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_history_date ON match_history(match_date);
CREATE INDEX IF NOT EXISTS idx_match_history_status ON match_history(status);
CREATE INDEX IF NOT EXISTS idx_match_history_type ON match_history(match_type);

-- Player statistics table
CREATE TABLE IF NOT EXISTS player_stats (
    player_id VARCHAR(100) PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    team VARCHAR(100),
    matches_played INTEGER DEFAULT 0 CHECK (matches_played >= 0),
    runs_scored INTEGER DEFAULT 0 CHECK (runs_scored >= 0),
    wickets_taken INTEGER DEFAULT 0 CHECK (wickets_taken >= 0),
    balls_faced INTEGER DEFAULT 0 CHECK (balls_faced >= 0),
    balls_bowled INTEGER DEFAULT 0 CHECK (balls_bowled >= 0),
    runs_conceded INTEGER DEFAULT 0 CHECK (runs_conceded >= 0),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_player_stats_name ON player_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_player_stats_team ON player_stats(team);

-- Team standings table
CREATE TABLE IF NOT EXISTS team_standings (
    team_name VARCHAR(100) NOT NULL,
    season VARCHAR(20) NOT NULL,
    matches_played INTEGER DEFAULT 0 CHECK (matches_played >= 0),
    wins INTEGER DEFAULT 0 CHECK (wins >= 0),
    losses INTEGER DEFAULT 0 CHECK (losses >= 0),
    no_result INTEGER DEFAULT 0 CHECK (no_result >= 0),
    points INTEGER DEFAULT 0 CHECK (points >= 0),
    net_run_rate DECIMAL(5,3) DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_name, season)
);

CREATE INDEX IF NOT EXISTS idx_team_standings_season ON team_standings(season, points DESC);

-- Achievements table
CREATE TABLE IF NOT EXISTS achievements (
    achievement_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    badge_type VARCHAR(50) NOT NULL,
    badge_name VARCHAR(100) NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_type ON achievements(badge_type);
