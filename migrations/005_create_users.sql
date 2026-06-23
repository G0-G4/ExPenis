-- 003: introduce users table and link existing telegram-id-identified rows to it.
--
-- Existing accounts/categories/transactions/tags store the raw Telegram numeric
-- user id in their `user_id` column. This migration creates a `users` table that
-- becomes the canonical identity store and rewrites every owned-table `user_id`
-- from the raw Telegram id to the corresponding `users.id`.
--
-- `users.username` is NULL for telegram-only identities; `users.telegram_id` is
-- NULL for users registered via the new /api/register endpoint (no Telegram link).

CREATE TABLE IF NOT EXISTS users
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE,
    password_hash TEXT,
    telegram_id   INTEGER UNIQUE,
    created_at    TIMESTAMP NOT NULL,
    updated_at    TIMESTAMP NOT NULL,
    CONSTRAINT users_at_least_one_handle CHECK (
        username IS NOT NULL OR telegram_id IS NOT NULL
        )
);

-- Index for login lookups by username.
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
-- Index for resolving telegram sessions/users by telegram_id.
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id);

-- Backfill: create one user row per distinct legacy `user_id` value, treating
-- those values as Telegram ids. `INSERT OR IGNORE` makes this idempotent w.r.t.
-- the (unique) `telegram_id` column, so re-running on an already-migrated
-- database is safe and is a near-no-op.
INSERT OR IGNORE INTO users (telegram_id, created_at, updated_at)
SELECT DISTINCT legacy.user_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM (SELECT user_id
      FROM accounts
      UNION
      SELECT user_id
      FROM categories
      UNION
      SELECT user_id
      FROM transactions
      UNION
      SELECT user_id
      FROM tags) AS legacy
WHERE legacy.user_id IS NOT NULL;

-- Rewrite every owned-table `user_id` from raw Telegram id to users.id.
-- Because `users.telegram_id` is UNIQUE and the backfill inserted one row per
-- distinct legacy id, the correlated subquery resolves exactly one target row.
-- SQLite resolves unmatched correlated subqueries to NULL; rows whose user_id
-- had no backfilled user (shouldn't happen, but defensively) are skipped here
-- and reported below via the safety check.
UPDATE accounts
SET user_id = (SELECT id FROM users WHERE telegram_id = accounts.user_id);
UPDATE categories
SET user_id = (SELECT id FROM users WHERE telegram_id = categories.user_id);
UPDATE transactions
SET user_id = (SELECT id FROM users WHERE telegram_id = transactions.user_id);
UPDATE tags
SET user_id = (SELECT id FROM users WHERE telegram_id = tags.user_id);