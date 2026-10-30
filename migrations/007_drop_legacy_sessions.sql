-- Telegram login sessions are no longer used; authentication uses JWT tokens.
DROP TABLE IF EXISTS sessions;
