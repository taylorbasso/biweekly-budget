from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from budget.models import (
    Account,
    CreditAccount,
    PaySchedule,
    RecurringExpense,
    User,
    ValidationError,
)

PAY_SCHEDULE_SQL = """
CREATE TABLE IF NOT EXISTS pay_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    anchor_date TEXT NOT NULL,
    amount INTEGER NOT NULL
);
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

""" + PAY_SCHEDULE_SQL + """
CREATE TABLE IF NOT EXISTS recurring_expense (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount INTEGER NOT NULL,
    recurrence_type TEXT NOT NULL,
    recurrence_value INTEGER NOT NULL,
    category TEXT,
    recurrence_anchor TEXT
);

CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    penalty_tax_percent INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS credit_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    interest_rate REAL NOT NULL DEFAULT 0,
    minimum_payment INTEGER NOT NULL DEFAULT 0,
    actual_payment INTEGER NOT NULL DEFAULT 0,
    credit_limit INTEGER NOT NULL DEFAULT 0
);
"""

OWNED_TABLES = ("pay_schedule", "recurring_expense", "account", "credit_account")


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate_add_recurrence_anchor(conn)
    _migrate_add_essential(conn)
    _migrate_add_credit_limit(conn)
    _migrate_add_user_ownership(conn)
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


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_add_user_ownership(conn: sqlite3.Connection) -> None:
    """Add per-account ownership. Pre-existing rows keep their data with user_id NULL,
    which no query returns until `claim-legacy` assigns them to an account."""
    for table in ("recurring_expense", "account", "credit_account"):
        if "user_id" not in _columns(conn, table):
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN "
                "user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
            )
    if "user_id" not in _columns(conn, "pay_schedule"):
        conn.execute("ALTER TABLE pay_schedule RENAME TO pay_schedule_old")
        conn.execute(PAY_SCHEDULE_SQL)
        conn.execute(
            "INSERT INTO pay_schedule (user_id, anchor_date, amount) "
            "SELECT NULL, anchor_date, amount FROM pay_schedule_old"
        )
        conn.execute("DROP TABLE pay_schedule_old")
    for table in ("recurring_expense", "account", "credit_account"):
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_user_id ON {table}(user_id)"
        )


def create_user(conn: sqlite3.Connection, email: str, password_hash: str) -> int:
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, password_hash, datetime.now(timezone.utc).isoformat()),
        )
    except sqlite3.IntegrityError as exc:
        raise ValidationError("That email is already registered") from exc
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def get_user(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute(
        "SELECT id, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return User(id=row["id"], email=row["email"])


def get_user_with_hash(conn: sqlite3.Connection, email: str) -> tuple[User, str] | None:
    row = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    if row is None:
        return None
    return User(id=row["id"], email=row["email"]), row["password_hash"]


def get_pay_schedule(conn: sqlite3.Connection, user_id: int) -> PaySchedule | None:
    row = conn.execute(
        "SELECT anchor_date, amount FROM pay_schedule WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return PaySchedule(anchor_date=date.fromisoformat(row["anchor_date"]), amount=row["amount"])


def set_pay_schedule(
    conn: sqlite3.Connection, user_id: int, pay_schedule: PaySchedule
) -> None:
    conn.execute(
        "INSERT INTO pay_schedule (user_id, anchor_date, amount) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "anchor_date = excluded.anchor_date, amount = excluded.amount",
        (user_id, pay_schedule.anchor_date.isoformat(), pay_schedule.amount),
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


def list_expenses(conn: sqlite3.Connection, user_id: int) -> list[RecurringExpense]:
    rows = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential FROM recurring_expense "
        "WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    return [_row_to_expense(row) for row in rows]


def get_expense(
    conn: sqlite3.Connection, user_id: int, expense_id: int
) -> RecurringExpense | None:
    row = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential FROM recurring_expense "
        "WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_expense(row)


def create_expense(
    conn: sqlite3.Connection, user_id: int, expense: RecurringExpense
) -> int:
    cursor = conn.execute(
        "INSERT INTO recurring_expense "
        "(user_id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
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
    conn: sqlite3.Connection, user_id: int, expense_id: int, expense: RecurringExpense
) -> None:
    conn.execute(
        "UPDATE recurring_expense SET name = ?, amount = ?, recurrence_type = ?, "
        "recurrence_value = ?, category = ?, recurrence_anchor = ?, essential = ? "
        "WHERE id = ? AND user_id = ?",
        (
            expense.name,
            expense.amount,
            expense.recurrence_type,
            expense.recurrence_value,
            expense.category,
            expense.recurrence_anchor.isoformat() if expense.recurrence_anchor else None,
            int(expense.essential),
            expense_id,
            user_id,
        ),
    )
    conn.commit()


def delete_expense(conn: sqlite3.Connection, user_id: int, expense_id: int) -> None:
    conn.execute(
        "DELETE FROM recurring_expense WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    conn.commit()


def _row_to_account(row: sqlite3.Row) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        balance=row["balance"],
        penalty_tax_percent=row["penalty_tax_percent"],
    )


def list_accounts(conn: sqlite3.Connection, user_id: int) -> list[Account]:
    rows = conn.execute(
        "SELECT id, name, balance, penalty_tax_percent FROM account "
        "WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    return [_row_to_account(row) for row in rows]


def get_account(
    conn: sqlite3.Connection, user_id: int, account_id: int
) -> Account | None:
    row = conn.execute(
        "SELECT id, name, balance, penalty_tax_percent FROM account "
        "WHERE id = ? AND user_id = ?",
        (account_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_account(row)


def create_account(conn: sqlite3.Connection, user_id: int, account: Account) -> int:
    cursor = conn.execute(
        "INSERT INTO account (user_id, name, balance, penalty_tax_percent) "
        "VALUES (?, ?, ?, ?)",
        (user_id, account.name, account.balance, account.penalty_tax_percent),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def update_account(
    conn: sqlite3.Connection, user_id: int, account_id: int, account: Account
) -> None:
    conn.execute(
        "UPDATE account SET name = ?, balance = ?, penalty_tax_percent = ? "
        "WHERE id = ? AND user_id = ?",
        (account.name, account.balance, account.penalty_tax_percent, account_id, user_id),
    )
    conn.commit()


def delete_account(conn: sqlite3.Connection, user_id: int, account_id: int) -> None:
    conn.execute(
        "DELETE FROM account WHERE id = ? AND user_id = ?", (account_id, user_id)
    )
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


def list_credit_accounts(conn: sqlite3.Connection, user_id: int) -> list[CreditAccount]:
    rows = conn.execute(
        "SELECT id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit FROM credit_account WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    return [_row_to_credit_account(row) for row in rows]


def get_credit_account(
    conn: sqlite3.Connection, user_id: int, credit_account_id: int
) -> CreditAccount | None:
    row = conn.execute(
        "SELECT id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit FROM credit_account WHERE id = ? AND user_id = ?",
        (credit_account_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_credit_account(row)


def create_credit_account(
    conn: sqlite3.Connection, user_id: int, credit_account: CreditAccount
) -> int:
    cursor = conn.execute(
        "INSERT INTO credit_account "
        "(user_id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
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
    conn: sqlite3.Connection,
    user_id: int,
    credit_account_id: int,
    credit_account: CreditAccount,
) -> None:
    conn.execute(
        "UPDATE credit_account SET name = ?, balance = ?, interest_rate = ?, "
        "minimum_payment = ?, actual_payment = ?, credit_limit = ? "
        "WHERE id = ? AND user_id = ?",
        (
            credit_account.name,
            credit_account.balance,
            credit_account.interest_rate,
            credit_account.minimum_payment,
            credit_account.actual_payment,
            credit_account.credit_limit,
            credit_account_id,
            user_id,
        ),
    )
    conn.commit()


def delete_credit_account(
    conn: sqlite3.Connection, user_id: int, credit_account_id: int
) -> None:
    conn.execute(
        "DELETE FROM credit_account WHERE id = ? AND user_id = ?",
        (credit_account_id, user_id),
    )
    conn.commit()


def claim_legacy_rows(conn: sqlite3.Connection, user_id: int) -> dict[str, int]:
    """Assign every unowned (pre-login) budget row to `user_id`, in one transaction.

    Refuses if the account already owns budget data, so nothing is ever merged.
    Returns the number of rows assigned per table.
    """
    for table in OWNED_TABLES:
        owned = conn.execute(
            f"SELECT 1 FROM {table} WHERE user_id = ? LIMIT 1", (user_id,)
        ).fetchone()
        if owned is not None:
            raise ValidationError(
                "That account already has budget data; refusing to merge"
            )
    counts: dict[str, int] = {}
    try:
        for table in OWNED_TABLES:
            cursor = conn.execute(
                f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (user_id,)
            )
            counts[table] = cursor.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return counts
