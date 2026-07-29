from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from budget.models import PaySchedule, RecurringExpense

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
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate_add_recurrence_anchor(conn)
    conn.commit()


def _migrate_add_recurrence_anchor(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(recurring_expense)")}
    if "recurrence_anchor" not in columns:
        conn.execute("ALTER TABLE recurring_expense ADD COLUMN recurrence_anchor TEXT")


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
    )


def list_expenses(conn: sqlite3.Connection) -> list[RecurringExpense]:
    rows = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor FROM recurring_expense ORDER BY id"
    ).fetchall()
    return [_row_to_expense(row) for row in rows]


def get_expense(conn: sqlite3.Connection, expense_id: int) -> RecurringExpense | None:
    row = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor FROM recurring_expense WHERE id = ?",
        (expense_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_expense(row)


def create_expense(conn: sqlite3.Connection, expense: RecurringExpense) -> int:
    cursor = conn.execute(
        "INSERT INTO recurring_expense "
        "(name, amount, recurrence_type, recurrence_value, category, recurrence_anchor) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            expense.name,
            expense.amount,
            expense.recurrence_type,
            expense.recurrence_value,
            expense.category,
            expense.recurrence_anchor.isoformat() if expense.recurrence_anchor else None,
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
        "recurrence_value = ?, category = ?, recurrence_anchor = ? WHERE id = ?",
        (
            expense.name,
            expense.amount,
            expense.recurrence_type,
            expense.recurrence_value,
            expense.category,
            expense.recurrence_anchor.isoformat() if expense.recurrence_anchor else None,
            expense_id,
        ),
    )
    conn.commit()


def delete_expense(conn: sqlite3.Connection, expense_id: int) -> None:
    conn.execute("DELETE FROM recurring_expense WHERE id = ?", (expense_id,))
    conn.commit()
