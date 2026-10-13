from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from click.testing import Result
from flask import Flask

from budget import db
from budget.app import create_app, get_db
from budget.auth import limiter
from budget.models import Account
from tests.conftest import make_user
from tests.integration.test_db_migration import OLD_SCHEMA


@pytest.fixture
def legacy_app(tmp_path: Path) -> Flask:
    path = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    conn.commit()
    conn.close()
    app = create_app(
        path,
        {"TESTING": True, "SECRET_KEY": "k", "WTF_CSRF_ENABLED": False, "SESSION_COOKIE_SECURE": False},
    )
    limiter.reset()
    return app


def _claim(app: Flask, email: str) -> Result:
    return app.test_cli_runner().invoke(args=["claim-legacy", "--email", email])


def test_claim_assigns_all_legacy_rows_unchanged(legacy_app: Flask) -> None:
    owner_id = make_user(legacy_app, "owner@example.com")
    result = _claim(legacy_app, "Owner@Example.com")
    assert result.exit_code == 0, result.output
    for table, count in [("pay_schedule", 1), ("recurring_expense", 2), ("account", 1), ("credit_account", 1)]:
        assert f"{table}: {count} row(s) assigned" in result.output
    with legacy_app.app_context():
        conn = get_db()
        schedule = db.get_pay_schedule(conn, owner_id)
        expenses = db.list_expenses(conn, owner_id)
        accounts = db.list_accounts(conn, owner_id)
        cards = db.list_credit_accounts(conn, owner_id)
    assert schedule is not None and schedule.amount == 200_000
    assert [e.name for e in expenses] == ["Rent", "Gym"]
    assert accounts[0].balance == 500_000 and accounts[0].penalty_tax_percent == 10
    assert cards[0].name == "Visa" and cards[0].interest_rate == 24.99


def test_unrelated_account_sees_nothing_before_or_after_claim(legacy_app: Flask) -> None:
    make_user(legacy_app, "owner@example.com")
    stranger_id = make_user(legacy_app, "stranger@example.com")
    stranger = legacy_app.test_client()
    stranger.post("/login", data={"email": "stranger@example.com", "password": "correct horse battery"})
    assert "Rent" not in stranger.get("/expenses").get_data(as_text=True)
    assert _claim(legacy_app, "owner@example.com").exit_code == 0
    assert "Rent" not in stranger.get("/expenses").get_data(as_text=True)
    with legacy_app.app_context():
        assert db.list_expenses(get_db(), stranger_id) == []


def test_claim_unknown_email_fails_and_changes_nothing(legacy_app: Flask) -> None:
    result = _claim(legacy_app, "nobody@example.com")
    assert result.exit_code != 0
    assert "No account with email" in result.output
    with legacy_app.app_context():
        unowned = get_db().execute("SELECT COUNT(*) FROM account WHERE user_id IS NULL").fetchone()[0]
    assert unowned == 1


def test_claim_refuses_account_that_already_has_data(legacy_app: Flask) -> None:
    owner_id = make_user(legacy_app, "owner@example.com")
    with legacy_app.app_context():
        db.create_account(get_db(), owner_id, Account(None, "Existing", 100))
    result = _claim(legacy_app, "owner@example.com")
    assert result.exit_code != 0
    assert "already has budget data" in result.output
    with legacy_app.app_context():
        unowned = get_db().execute("SELECT COUNT(*) FROM recurring_expense WHERE user_id IS NULL").fetchone()[0]
    assert unowned == 2


def test_claim_does_not_touch_rows_owned_by_others(legacy_app: Flask) -> None:
    owner_id = make_user(legacy_app, "owner@example.com")
    other_id = make_user(legacy_app, "other@example.com")
    with legacy_app.app_context():
        db.create_account(get_db(), other_id, Account(None, "Others", 100))
    assert _claim(legacy_app, "owner@example.com").exit_code == 0
    with legacy_app.app_context():
        assert [a.name for a in db.list_accounts(get_db(), other_id)] == ["Others"]
        assert [a.name for a in db.list_accounts(get_db(), owner_id)] == ["Savings"]
