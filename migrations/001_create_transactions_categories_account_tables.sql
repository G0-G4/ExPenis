CREATE TABLE IF NOT EXISTS transactions
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    account_id  INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions (user_id);
CREATE INDEX IF  NOT EXISTS  idx_transactions_created_at ON transactions (created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions (account_id);


CREATE TABLE IF NOT EXISTS  categories
(
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    type       TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    name       TEXT    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories (user_id);
CREATE INDEX IF NOT EXISTS idx_categories_type ON categories (type);
CREATE INDEX IF NOT EXISTS idx_categories_type ON categories (name);

-- Create accounts table
CREATE TABLE IF NOT EXISTS  accounts
(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    name              TEXT    NOT NULL,
    adjustment_amount REAL    NOT NULL DEFAULT 0.0,
    created_at        TIMESTAMP        DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP        DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id);
