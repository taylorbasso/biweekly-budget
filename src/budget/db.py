from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from budget.models import Account, CreditAccount, PaySchedule, RecurringExpense

SCHEMA = """
CREATE TABLE IF NOT EXISTS pay_schedule (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    anchor_date TEXT NOT NULL,
    amount INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_expense (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount INTEGER NOT NULL,
    recurrence_type TEXT NOT NULL,
    recurrence_value INTEGER NOT NULL,
    category TEXT,
    recurrence_anchor TEXT
);

CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    penalty_tax_percent INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS credit_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    interest_rate REAL NOT NULL DEFAULT 0,
    minimum_payment INTEGER NOT NULL DEFAULT 0,
    actual_payment INTEGER NOT NULL DEFAULT 0,
    credit_limit INTEGER NOT NULL DEFAULT 0
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate_add_recurrence_anchor(conn)
    _migrate_add_essential(conn)
    _migrate_add_credit_limit(conn)
    conn.commit()


def _migrate_add_recurrence_anchor(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(recurring_expense)")}
    if "recurrence_anchor" not in columns:
        conn.execute("ALTER TABLE recurring_expense ADD COLUMN recurrence_anchor TEXT")


def _migrate_add_essential(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(recurring_expense)")}
    if "essential" not in columns:
        conn.execute(
            "ALTER TABLE recurring_expense ADD COLUMN essential INTEGER NOT NULL DEFAULT 0"
        )


def _migrate_add_credit_limit(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(credit_account)")}
    if "credit_limit" not in columns:
        conn.execute(
            "ALTER TABLE credit_account ADD COLUMN credit_limit INTEGER NOT NULL DEFAULT 0"
        )


def get_pay_schedule(conn: sqlite3.Connection) -> PaySchedule | None:
    row = conn.execute(
        "SELECT anchor_date, amount FROM pay_schedule WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    return PaySchedule(anchor_date=date.fromisoformat(row["anchor_date"]), amount=row["amount"])


def set_pay_schedule(conn: sqlite3.Connection, pay_schedule: PaySchedule) -> None:
    conn.execute(
        "INSERT INTO pay_schedule (id, anchor_date, amount) VALUES (1, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "anchor_date = excluded.anchor_date, amount = excluded.amount",
        (pay_schedule.anchor_date.isoformat(), pay_schedule.amount),
    )
    conn.commit()


def _row_to_expense(row: sqlite3.Row) -> RecurringExpense:
    anchor = row["recurrence_anchor"]
    return RecurringExpense(
        id=row["id"],
        name=row["name"],
        amount=row["amount"],
        recurrence_type=row["recurrence_type"],
        recurrence_value=row["recurrence_value"],
        category=row["category"],
        recurrence_anchor=date.fromisoformat(anchor) if anchor else None,
        essential=bool(row["essential"]),
    )


def list_expenses(conn: sqlite3.Connection) -> list[RecurringExpense]:
    rows = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential FROM recurring_expense ORDER BY id"
    ).fetchall()
    return [_row_to_expense(row) for row in rows]


def get_expense(conn: sqlite3.Connection, expense_id: int) -> RecurringExpense | None:
    row = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential FROM recurring_expense WHERE id = ?",
        (expense_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_expense(row)


def create_expense(conn: sqlite3.Connection, expense: RecurringExpense) -> int:
    cursor = conn.execute(
        "INSERT INTO recurring_expense "
        "(name, amount, recurrence_type, recurrence_value, category, recurrence_anchor, "
        "essential) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            expense.name,
            expense.amount,
            expense.recurrence_type,
            expense.recurrence_value,
            expense.category,
            expense.recurrence_anchor.isoformat() if expense.recurrence_anchor else None,
            int(expense.essential),
        ),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def update_expense(
    conn: sqlite3.Connection, expense_id: int, expense: RecurringExpense
) -> None:
    conn.execute(
        "UPDATE recurring_expense SET name = ?, amount = ?, recurrence_type = ?, "
        "recurrence_value = ?, category = ?, recurrence_anchor = ?, essential = ? "
        "WHERE id = ?",
        (
            expense.name,
            expense.amount,
            expense.recurrence_type,
            expense.recurrence_value,
            expense.category,
            expense.recurrence_anchor.isoformat() if expense.recurrence_anchor else None,
            int(expense.essential),
            expense_id,
        ),
    )
    conn.commit()


def delete_expense(conn: sqlite3.Connection, expense_id: int) -> None:
    conn.execute("DELETE FROM recurring_expense WHERE id = ?", (expense_id,))
    conn.commit()


def _row_to_account(row: sqlite3.Row) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        balance=row["balance"],
        penalty_tax_percent=row["penalty_tax_percent"],
    )


def list_accounts(conn: sqlite3.Connection) -> list[Account]:
    rows = conn.execute(
        "SELECT id, name, balance, penalty_tax_percent FROM account ORDER BY id"
    ).fetchall()
    return [_row_to_account(row) for row in rows]


def get_account(conn: sqlite3.Connection, account_id: int) -> Account | None:
    row = conn.execute(
        "SELECT id, name, balance, penalty_tax_percent FROM account WHERE id = ?",
        (account_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_account(row)


def create_account(conn: sqlite3.Connection, account: Account) -> int:
    cursor = conn.execute(
        "INSERT INTO account (name, balance, penalty_tax_percent) VALUES (?, ?, ?)",
        (account.name, account.balance, account.penalty_tax_percent),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def update_account(conn: sqlite3.Connection, account_id: int, account: Account) -> None:
    conn.execute(
        "UPDATE account SET name = ?, balance = ?, penalty_tax_percent = ? WHERE id = ?",
        (account.name, account.balance, account.penalty_tax_percent, account_id),
    )
    conn.commit()


def delete_account(conn: sqlite3.Connection, account_id: int) -> None:
    conn.execute("DELETE FROM account WHERE id = ?", (account_id,))
    conn.commit()


def _row_to_credit_account(row: sqlite3.Row) -> CreditAccount:
    return CreditAccount(
        id=row["id"],
        name=row["name"],
        balance=row["balance"],
        interest_rate=row["interest_rate"],
        minimum_payment=row["minimum_payment"],
        actual_payment=row["actual_payment"],
        credit_limit=row["credit_limit"],
    )


def list_credit_accounts(conn: sqlite3.Connection) -> list[CreditAccount]:
    rows = conn.execute(
        "SELECT id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit FROM credit_account ORDER BY id"
    ).fetchall()
    return [_row_to_credit_account(row) for row in rows]


def get_credit_account(
    conn: sqlite3.Connection, credit_account_id: int
) -> CreditAccount | None:
    row = conn.execute(
        "SELECT id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit FROM credit_account WHERE id = ?",
        (credit_account_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_credit_account(row)


def create_credit_account(conn: sqlite3.Connection, credit_account: CreditAccount) -> int:
    cursor = conn.execute(
        "INSERT INTO credit_account "
        "(name, balance, interest_rate, minimum_payment, actual_payment, credit_limit) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            credit_account.name,
            credit_account.balance,
            credit_account.interest_rate,
            credit_account.minimum_payment,
            credit_account.actual_payment,
            credit_account.credit_limit,
        ),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def update_credit_account(
    conn: sqlite3.Connection, credit_account_id: int, credit_account: CreditAccount
) -> None:
    conn.execute(
        "UPDATE credit_account SET name = ?, balance = ?, interest_rate = ?, "
        "minimum_payment = ?, actual_payment = ?, credit_limit = ? WHERE id = ?",
        (
            credit_account.name,
            credit_account.balance,
            credit_account.interest_rate,
            credit_account.minimum_payment,
            credit_account.actual_payment,
            credit_account.credit_limit,
            credit_account_id,
        ),
    )
    conn.commit()


def delete_credit_account(conn: sqlite3.Connection, credit_account_id: int) -> None:
    conn.execute("DELETE FROM credit_account WHERE id = ?", (credit_account_id,))
    conn.commit()
