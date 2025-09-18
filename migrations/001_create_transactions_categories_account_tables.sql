CREATE TABLE transactions
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    type       TEXT    NOT NULL,
    category   TEXT    NOT NULL,
    amount     REAL    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE INDEX idx_transactions_user_id ON transactions (user_id);
CREATE INDEX idx_transactions_type ON transactions (type);
CREATE INDEX idx_transactions_category ON transactions (category);
CREATE INDEX idx_transactions_created_at ON transactions (created_at);
CREATE INDEX idx_transactions_account_id ON transactions (account_id);


CREATE TABLE categories
(
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    type       TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    name       TEXT    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_user_id ON categories (user_id);
CREATE INDEX idx_categories_type ON categories (type);

-- Create accounts table
CREATE TABLE accounts
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT    NOT NULL,
    amount     REAL    NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP        DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP        DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_user_id ON accounts (user_id);