CREATE TABLE personal_greetings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    assignment_id TEXT NOT NULL UNIQUE,
    text TEXT NOT NULL,
    expires_at DATETIME,
    dismissed_at DATETIME,
    created_at DATETIME NOT NULL
);
