CREATE TABLE IF NOT EXISTS users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS pay_schedule (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    anchor_date DATE NOT NULL,
    amount BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_expense (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount BIGINT NOT NULL,
    recurrence_type TEXT NOT NULL,
    recurrence_value INTEGER NOT NULL,
    category TEXT,
    recurrence_anchor DATE,
    essential BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_recurring_expense_user_id ON recurring_expense(user_id);

CREATE TABLE IF NOT EXISTS account (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    balance BIGINT NOT NULL,
    penalty_tax_percent INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_account_user_id ON account(user_id);

-- Replaced by the debt table (2026-10-20); never held production data.
DROP TABLE IF EXISTS credit_account;

CREATE TABLE IF NOT EXISTS debt (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    balance BIGINT NOT NULL,
    interest_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
    minimum_payment BIGINT NOT NULL DEFAULT 0,
    actual_payment BIGINT NOT NULL DEFAULT 0,
    credit_limit BIGINT NOT NULL DEFAULT 0,
    kind TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_debt_user_id ON debt(user_id);
