CREATE TABLE IF NOT EXISTS sessions
(
    id         TEXT PRIMARY KEY,
    user_id    INTEGER NULL,
    status     TEXT CHECK (status IN ('pending', 'confirmed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
