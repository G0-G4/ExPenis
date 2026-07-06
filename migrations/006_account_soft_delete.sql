ALTER TABLE accounts ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN deleted_at TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS idx_accounts_user_deleted ON accounts(user_id, is_deleted);