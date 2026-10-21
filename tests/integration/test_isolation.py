"""One account must never read, change, or delete another account's records."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from flask import Flask
from flask.testing import FlaskClient

from budget import db
from budget.app import get_db
from budget.models import Account, Debt, PaySchedule, RecurringExpense

NewClient = Callable[[str], tuple[FlaskClient, int]]


def _seed_account_a(app: Flask, user_id: int) -> dict[str, int]:
    with app.app_context():
        conn = get_db()
        db.set_pay_schedule(conn, user_id, PaySchedule(date(2026, 7, 31), 250_000))
        return {
            "expense": db.create_expense(
                conn,
                user_id,
                RecurringExpense(None, "A-Rent-Secret", 120_000, "day_of_month", 1),
            ),
            "savings": db.create_account(conn, user_id, Account(None, "A-Savings-Secret", 500_000)),
            "card": db.create_debt(
                conn, user_id, Debt(None, "A-Visa-Secret", 100_000)
            ),
        }


def test_other_account_sees_none_of_my_data(
    app: Flask,
    user_id: int,
    logged_in_client: FlaskClient,
    new_logged_in_client: NewClient,
) -> None:
    _seed_account_a(app, user_id)
    # Positive control: the owner does see their own data on these pages.
    assert "A-Rent-Secret" in logged_in_client.get("/expenses").get_data(as_text=True)
    assert "A-Savings-Secret" in logged_in_client.get("/runway").get_data(as_text=True)
    assert "A-Visa-Secret" in logged_in_client.get("/debt").get_data(as_text=True)
    client_b, _ = new_logged_in_client("b@example.com")
    for path in ("/", "/expenses", "/annual-cost", "/runway", "/debt", "/pay-schedule"):
        page = client_b.get(path).get_data(as_text=True)
        assert "Secret" not in page, path
        assert "2,500.00" not in page, path


def test_other_account_cannot_open_edit_pages_by_id(
    app: Flask, user_id: int, new_logged_in_client: NewClient
) -> None:
    ids = _seed_account_a(app, user_id)
    client_b, _ = new_logged_in_client("b@example.com")
    assert client_b.get(f"/expenses/{ids['expense']}/edit").status_code == 404
    assert client_b.get(f"/runway/accounts/{ids['savings']}/edit").status_code == 404
    assert client_b.get(f"/debt/{ids['card']}/edit").status_code == 404


def test_other_account_cannot_change_or_delete_by_id(
    app: Flask, user_id: int, new_logged_in_client: NewClient
) -> None:
    ids = _seed_account_a(app, user_id)
    client_b, _ = new_logged_in_client("b@example.com")
    attempts = [
        f"/expenses/{ids['expense']}/edit",
        f"/expenses/{ids['expense']}/delete",
        f"/runway/accounts/{ids['savings']}/edit",
        f"/runway/accounts/{ids['savings']}/delete",
        f"/debt/{ids['card']}/edit",
        f"/debt/{ids['card']}/delete",
    ]
    for path in attempts:
        data = {"name": "Hacked", "amount": "1.00", "balance": "1.00"}
        assert client_b.post(path, data=data).status_code == 404, path

    with app.app_context():
        conn = get_db()
        expense = db.get_expense(conn, user_id, ids["expense"])
        savings = db.get_account(conn, user_id, ids["savings"])
        card = db.get_debt(conn, user_id, ids["card"])
    assert expense is not None and expense.name == "A-Rent-Secret" and not expense.essential
    assert savings is not None and savings.name == "A-Savings-Secret"
    assert card is not None and card.name == "A-Visa-Secret"


def test_other_accounts_pay_schedule_is_separate(
    app: Flask, user_id: int, new_logged_in_client: NewClient
) -> None:
    _seed_account_a(app, user_id)
    client_b, b_id = new_logged_in_client("b@example.com")
    response = client_b.post("/pay-schedule", data={"anchor_date": "2026-08-07", "amount": "999.00"})
    assert response.status_code == 302
    with app.app_context():
        conn = get_db()
        a_schedule = db.get_pay_schedule(conn, user_id)
        b_schedule = db.get_pay_schedule(conn, b_id)
    assert a_schedule is not None and a_schedule.amount == 250_000
    assert b_schedule is not None and b_schedule.amount == 99_900


def test_new_account_starts_empty(
    app: Flask, user_id: int, new_logged_in_client: NewClient
) -> None:
    _seed_account_a(app, user_id)
    _, b_id = new_logged_in_client("b@example.com")
    with app.app_context():
        conn = get_db()
        assert db.get_pay_schedule(conn, b_id) is None
        assert db.list_expenses(conn, b_id) == []
        assert db.list_accounts(conn, b_id) == []
        assert db.list_debts(conn, b_id) == []
