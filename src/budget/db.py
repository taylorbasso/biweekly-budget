from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from budget.models import (
    Account,
    Debt,
    PaySchedule,
    RecurringExpense,
    User,
    ValidationError,
)

Connection = psycopg.Connection[dict[str, Any]]

SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def connect() -> Connection:
    """Connect using libpq's standard PG* environment variables."""
    return psycopg.connect("", row_factory=dict_row, connect_timeout=30)


def init_db(conn: Connection) -> None:
    conn.execute(SCHEMA_FILE.read_text())
    conn.commit()


def create_user(conn: Connection, email: str, password_hash: str) -> int:
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (%s, %s, %s) "
            "RETURNING id",
            (email, password_hash, datetime.now(timezone.utc)),
        )
    except psycopg.errors.UniqueViolation as exc:
        conn.rollback()
        raise ValidationError("That email is already registered") from exc
    conn.commit()
    row = cursor.fetchone()
    assert row is not None
    return int(row["id"])


def get_user(conn: Connection, user_id: int) -> User | None:
    row = conn.execute(
        "SELECT id, email FROM users WHERE id = %s", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return User(id=row["id"], email=row["email"])


def get_user_with_hash(conn: Connection, email: str) -> tuple[User, str] | None:
    row = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE email = %s", (email,)
    ).fetchone()
    if row is None:
        return None
    return User(id=row["id"], email=row["email"]), row["password_hash"]


def get_pay_schedule(conn: Connection, user_id: int) -> PaySchedule | None:
    row = conn.execute(
        "SELECT anchor_date, amount FROM pay_schedule WHERE user_id = %s", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return PaySchedule(anchor_date=row["anchor_date"], amount=row["amount"])


def set_pay_schedule(
    conn: Connection, user_id: int, pay_schedule: PaySchedule
) -> None:
    conn.execute(
        "INSERT INTO pay_schedule (user_id, anchor_date, amount) VALUES (%s, %s, %s) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "anchor_date = excluded.anchor_date, amount = excluded.amount",
        (user_id, pay_schedule.anchor_date, pay_schedule.amount),
    )
    conn.commit()


def _row_to_expense(row: dict[str, Any]) -> RecurringExpense:
    return RecurringExpense(
        id=row["id"],
        name=row["name"],
        amount=row["amount"],
        recurrence_type=row["recurrence_type"],
        recurrence_value=row["recurrence_value"],
        category=row["category"],
        recurrence_anchor=row["recurrence_anchor"],
        essential=row["essential"],
    )


def list_expenses(conn: Connection, user_id: int) -> list[RecurringExpense]:
    rows = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential FROM recurring_expense "
        "WHERE user_id = %s ORDER BY id",
        (user_id,),
    ).fetchall()
    return [_row_to_expense(row) for row in rows]


def get_expense(
    conn: Connection, user_id: int, expense_id: int
) -> RecurringExpense | None:
    row = conn.execute(
        "SELECT id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential FROM recurring_expense "
        "WHERE id = %s AND user_id = %s",
        (expense_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_expense(row)


def create_expense(
    conn: Connection, user_id: int, expense: RecurringExpense
) -> int:
    cursor = conn.execute(
        "INSERT INTO recurring_expense "
        "(user_id, name, amount, recurrence_type, recurrence_value, category, "
        "recurrence_anchor, essential) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            user_id,
            expense.name,
            expense.amount,
            expense.recurrence_type,
            expense.recurrence_value,
            expense.category,
            expense.recurrence_anchor,
            expense.essential,
        ),
    )
    conn.commit()
    row = cursor.fetchone()
    assert row is not None
    return int(row["id"])


def update_expense(
    conn: Connection, user_id: int, expense_id: int, expense: RecurringExpense
) -> None:
    conn.execute(
        "UPDATE recurring_expense SET name = %s, amount = %s, recurrence_type = %s, "
        "recurrence_value = %s, category = %s, recurrence_anchor = %s, essential = %s "
        "WHERE id = %s AND user_id = %s",
        (
            expense.name,
            expense.amount,
            expense.recurrence_type,
            expense.recurrence_value,
            expense.category,
            expense.recurrence_anchor,
            expense.essential,
            expense_id,
            user_id,
        ),
    )
    conn.commit()


def delete_expense(conn: Connection, user_id: int, expense_id: int) -> None:
    conn.execute(
        "DELETE FROM recurring_expense WHERE id = %s AND user_id = %s",
        (expense_id, user_id),
    )
    conn.commit()


def _row_to_account(row: dict[str, Any]) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        balance=row["balance"],
        penalty_tax_percent=row["penalty_tax_percent"],
    )


def list_accounts(conn: Connection, user_id: int) -> list[Account]:
    rows = conn.execute(
        "SELECT id, name, balance, penalty_tax_percent FROM account "
        "WHERE user_id = %s ORDER BY id",
        (user_id,),
    ).fetchall()
    return [_row_to_account(row) for row in rows]


def get_account(
    conn: Connection, user_id: int, account_id: int
) -> Account | None:
    row = conn.execute(
        "SELECT id, name, balance, penalty_tax_percent FROM account "
        "WHERE id = %s AND user_id = %s",
        (account_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_account(row)


def create_account(conn: Connection, user_id: int, account: Account) -> int:
    cursor = conn.execute(
        "INSERT INTO account (user_id, name, balance, penalty_tax_percent) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (user_id, account.name, account.balance, account.penalty_tax_percent),
    )
    conn.commit()
    row = cursor.fetchone()
    assert row is not None
    return int(row["id"])


def update_account(
    conn: Connection, user_id: int, account_id: int, account: Account
) -> None:
    conn.execute(
        "UPDATE account SET name = %s, balance = %s, penalty_tax_percent = %s "
        "WHERE id = %s AND user_id = %s",
        (account.name, account.balance, account.penalty_tax_percent, account_id, user_id),
    )
    conn.commit()


def delete_account(conn: Connection, user_id: int, account_id: int) -> None:
    conn.execute(
        "DELETE FROM account WHERE id = %s AND user_id = %s", (account_id, user_id)
    )
    conn.commit()


def _row_to_debt(row: dict[str, Any]) -> Debt:
    return Debt(
        id=row["id"],
        name=row["name"],
        balance=row["balance"],
        interest_rate=row["interest_rate"],
        minimum_payment=row["minimum_payment"],
        actual_payment=row["actual_payment"],
        credit_limit=row["credit_limit"],
        kind=row["kind"],
    )


def list_debts(conn: Connection, user_id: int) -> list[Debt]:
    rows = conn.execute(
        "SELECT id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit, kind FROM debt WHERE user_id = %s ORDER BY id",
        (user_id,),
    ).fetchall()
    return [_row_to_debt(row) for row in rows]


def get_debt(
    conn: Connection, user_id: int, debt_id: int
) -> Debt | None:
    row = conn.execute(
        "SELECT id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit, kind FROM debt WHERE id = %s AND user_id = %s",
        (debt_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_debt(row)


def create_debt(
    conn: Connection, user_id: int, debt: Debt
) -> int:
    cursor = conn.execute(
        "INSERT INTO debt "
        "(user_id, name, balance, interest_rate, minimum_payment, actual_payment, "
        "credit_limit, kind) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            user_id,
            debt.name,
            debt.balance,
            debt.interest_rate,
            debt.minimum_payment,
            debt.actual_payment,
            debt.credit_limit,
            debt.kind,
        ),
    )
    conn.commit()
    row = cursor.fetchone()
    assert row is not None
    return int(row["id"])


def update_debt(
    conn: Connection,
    user_id: int,
    debt_id: int,
    debt: Debt,
) -> None:
    conn.execute(
        "UPDATE debt SET name = %s, balance = %s, interest_rate = %s, "
        "minimum_payment = %s, actual_payment = %s, credit_limit = %s, kind = %s "
        "WHERE id = %s AND user_id = %s",
        (
            debt.name,
            debt.balance,
            debt.interest_rate,
            debt.minimum_payment,
            debt.actual_payment,
            debt.credit_limit,
            debt.kind,
            debt_id,
            user_id,
        ),
    )
    conn.commit()


def delete_debt(
    conn: Connection, user_id: int, debt_id: int
) -> None:
    conn.execute(
        "DELETE FROM debt WHERE id = %s AND user_id = %s",
        (debt_id, user_id),
    )
    conn.commit()
