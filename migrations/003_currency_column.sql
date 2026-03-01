ALTER TABLE main.accounts
ADD COLUMN currency_code VARCHAR(10) NOT NULL DEFAULT 'RUB';

ALTER TABLE main.transactions
ADD COLUMN exchange_rate REAL NOT NULL  DEFAULT 1.0;
