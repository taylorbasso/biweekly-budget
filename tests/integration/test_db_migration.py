"""Pre-login databases must migrate without losing data, leaving rows unowned."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from budget import db

# The schema as it was before login existed (feature 005).
OLD_SCHEMA = """
CREATE TABLE pay_schedule (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    anchor_date TEXT NOT NULL,
    amount INTEGER NOT NULL
);
CREATE TABLE recurring_expense (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount INTEGER NOT NULL,
    recurrence_type TEXT NOT NULL,
    recurrence_value INTEGER NOT NULL,
    category TEXT,
    recurrence_anchor TEXT
);
CREATE TABLE account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    penalty_tax_percent INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE credit_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    interest_rate REAL NOT NULL DEFAULT 0,
    minimum_payment INTEGER NOT NULL DEFAULT 0,
    actual_payment INTEGER NOT NULL DEFAULT 0
);
INSERT INTO pay_schedule (id, anchor_date, amount) VALUES (1, '2026-07-31', 200000);
INSERT INTO recurring_expense (name, amount, recurrence_type, recurrence_value, category)
    VALUES ('Rent', 120000, 'day_of_month', 1, 'Housing'),
           ('Gym', 3000, 'day_of_month', 5, NULL);
INSERT INTO account (name, balance, penalty_tax_percent) VALUES ('Savings', 500000, 10);
INSERT INTO credit_account (name, balance, interest_rate, minimum_payment, actual_payment)
    VALUES ('Visa', 150000, 24.99, 3000, 5000);
"""


@pytest.fixture
def old_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "old.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    conn.commit()
    conn.close()
    return path


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_migration_preserves_every_row_as_unowned(old_db_path: Path) -> None:
    conn = db.connect(old_db_path)
    db.init_db(conn)
    assert _count(conn, "pay_schedule") == 1
    assert _count(conn, "recurring_expense") == 2
    assert _count(conn, "account") == 1
    assert _count(conn, "credit_account") == 1
    for table in db.OWNED_TABLES:
        owners = conn.execute(f"SELECT DISTINCT user_id FROM {table}").fetchall()
        assert [row["user_id"] for row in owners] == [None], table
    schedule = conn.execute("SELECT anchor_date, amount FROM pay_schedule").fetchone()
    assert (schedule["anchor_date"], schedule["amount"]) == ("2026-07-31", 200000)


def test_migration_is_idempotent(old_db_path: Path) -> None:
    conn = db.connect(old_db_path)
    db.init_db(conn)
    db.init_db(conn)
    assert _count(conn, "recurring_expense") == 2
    assert _count(conn, "pay_schedule") == 1


def test_unowned_rows_are_invisible_to_every_account(old_db_path: Path) -> None:
    conn = db.connect(old_db_path)
    db.init_db(conn)
    user_id = db.create_user(conn, "someone@example.com", "hash")
    assert db.get_pay_schedule(conn, user_id) is None
    assert db.list_expenses(conn, user_id) == []
    assert db.list_accounts(conn, user_id) == []
    assert db.list_credit_accounts(conn, user_id) == []
    # Even by guessing a legacy row's id.
    assert db.get_expense(conn, user_id, 1) is None
    assert db.get_account(conn, user_id, 1) is None
    assert db.get_credit_account(conn, user_id, 1) is None


def test_foreign_keys_cascade_when_an_account_is_deleted(old_db_path: Path) -> None:
    conn = db.connect(old_db_path)
    db.init_db(conn)
    user_id = db.create_user(conn, "gone@example.com", "hash")
    conn.execute(
        "INSERT INTO account (user_id, name, balance) VALUES (?, 'Mine', 100)", (user_id,)
    )
    conn.commit()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    assert db.list_accounts(conn, user_id) == []
    assert _count(conn, "account") == 1  # only the unowned legacy row remains
