from __future__ import annotations

from datetime import date

import pytest
from flask import Flask
from flask.testing import FlaskClient

from budget import db
from budget.app import get_db
from budget.models import Account, Debt, PaySchedule, RecurringExpense
from tests.conftest import TEST_EMAIL, login


def _owner_id(app: Flask) -> int:
    """Id of the signed-in test account that owns everything these tests seed."""
    with app.app_context():
        found = db.get_user_with_hash(get_db(), TEST_EMAIL)
    assert found is not None
    return found[0].id


@pytest.fixture
def client(app: Flask, user_id: int) -> FlaskClient:
    """Shadows the anonymous conftest client: signed in as the owner account."""
    signed_in = app.test_client()
    login(signed_in)
    return signed_in


def _seed_pay_schedule(app, anchor_date: date, amount: int) -> None:
    with app.app_context():
        conn = get_db()
        db.set_pay_schedule(conn, _owner_id(app), PaySchedule(anchor_date=anchor_date, amount=amount))


def _seed_expense(
    app,
    name: str,
    amount: int,
    recurrence_type: str,
    recurrence_value: int,
    category: str | None = None,
    essential: bool = False,
) -> int:
    with app.app_context():
        conn = get_db()
        return db.create_expense(
            conn,
            _owner_id(app),
            RecurringExpense(
                id=None,
                name=name,
                amount=amount,
                recurrence_type=recurrence_type,
                recurrence_value=recurrence_value,
                category=category,
                essential=essential,
            ),
        )


def _seed_account(
    app, name: str, balance: int, penalty_tax_percent: int = 0
) -> int:
    with app.app_context():
        conn = get_db()
        return db.create_account(
            conn,
            _owner_id(app),
            Account(
                id=None,
                name=name,
                balance=balance,
                penalty_tax_percent=penalty_tax_percent,
            ),
        )


def _seed_debt(
    app,
    name: str,
    balance: int,
    interest_rate: float = 0,
    minimum_payment: int = 0,
    actual_payment: int = 0,
    credit_limit: int = 0,
    kind: str = "credit_card",
) -> int:
    with app.app_context():
        conn = get_db()
        return db.create_debt(
            conn,
            _owner_id(app),
            Debt(
                id=None,
                name=name,
                balance=balance,
                interest_rate=interest_rate,
                minimum_payment=minimum_payment,
                actual_payment=actual_payment,
                credit_limit=credit_limit,
                kind=kind,
            ),
        )


def test_home_page_renders_chart_slices_for_seeded_cycle(app, client: FlaskClient) -> None:
    _seed_pay_schedule(app, date(2026, 7, 31), 200_000)
    _seed_expense(app, "Rent", 120_000, "day_of_month", 1, category="Housing")
    _seed_expense(app, "Investment", 10_000, "day_of_week", 4, category="Investments")
    _seed_expense(app, "Streaming", 1_500, "day_of_month", 31)

    response = client.get("/?date=2026-08-01")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '<svg viewBox="0 0 200 200" class="cycle-chart"' in body
    assert "Housing" in body
    assert "Investments" in body
    assert "Uncategorized" in body
    assert "</span>Leftover" in body


def test_home_page_chart_follows_selected_cycle(app, client: FlaskClient) -> None:
    _seed_pay_schedule(app, date(2026, 7, 31), 200_000)
    _seed_expense(app, "Rent", 120_000, "day_of_month", 1, category="Housing")

    current = client.get("/?date=2026-08-01").get_data(as_text=True)
    next_cycle = client.get("/?date=2026-08-14").get_data(as_text=True)

    assert "Housing" in current
    assert "Housing" not in next_cycle


def test_home_page_without_pay_schedule_renders_no_chart(app, client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Set up your pay schedule" in body
    assert "cycle-chart" not in body


def test_home_page_overspent_cycle_omits_leftover_slice(app, client: FlaskClient) -> None:
    _seed_pay_schedule(app, date(2026, 7, 31), 100_00)
    _seed_expense(app, "Big bill", 500_00, "day_of_month", 1, category="Housing")

    response = client.get("/?date=2026-08-01")

    body = response.get_data(as_text=True)
    assert "Overspent this cycle" in body
    assert "</span>Leftover" not in body


def test_annual_cost_page_shows_each_expenses_annual_cost(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 120_000, "day_of_month", 1, category="Housing")
    _seed_expense(
        app, "Investment transfer", 10_000, "day_of_week", 4, category="Investments"
    )
    _seed_expense(app, "Streaming", 1_500, "day_of_month", 31)

    response = client.get("/annual-cost")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Rent" in body
    assert "$14,400.00" in body or "$14400.00" in body
    assert "Investment transfer" in body
    assert "$5,200.00" in body or "$5200.00" in body
    assert "Streaming" in body
    assert "$180.00" in body
    assert "$19,780.00" in body or "$19780.00" in body
    assert "$1,648.33/mo" in body


def test_annual_cost_page_empty_state_shows_zero_grand_total(
    app, client: FlaskClient
) -> None:
    response = client.get("/annual-cost")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "No expenses recorded" in body
    assert "$0.00" in body


def test_runway_single_account_matches_quickstart_scenario_a(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)
    client.post(
        "/runway/accounts",
        data={"name": "Cash", "balance": "7060.00", "penalty_tax_percent": "0"},
    )

    response = client.get("/runway")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "3.53 months" in body


def test_runway_multiple_accounts_matches_quickstart_scenario_b(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)
    client.post(
        "/runway/accounts",
        data={"name": "Cash", "balance": "2000.00", "penalty_tax_percent": "0"},
    )
    client.post(
        "/runway/accounts",
        data={"name": "401k", "balance": "10000.00", "penalty_tax_percent": "30"},
    )

    response = client.get("/runway")

    assert response.status_code == 200
    assert "4.50 months" in response.get_data(as_text=True)


def test_runway_no_essential_expenses_shows_message(app, client: FlaskClient) -> None:
    _seed_expense(app, "Streaming", 1_500, "day_of_month", 31)
    _seed_account(app, "Cash", 706_000, 0)

    response = client.get("/runway")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "No essential expenses selected" in body


def test_runway_no_accounts_shows_zero_months(app, client: FlaskClient) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)

    response = client.get("/runway")

    assert response.status_code == 200
    assert "0.00 months" in response.get_data(as_text=True)


def test_account_edit_prefills_and_updates(app, client: FlaskClient) -> None:
    account_id = _seed_account(app, "Cash", 100_000, 0)

    edit_response = client.get(f"/runway/accounts/{account_id}/edit")
    assert edit_response.status_code == 200
    assert "1000.00" in edit_response.get_data(as_text=True)

    update_response = client.post(
        f"/runway/accounts/{account_id}/edit",
        data={"name": "Cash", "balance": "2000.00", "penalty_tax_percent": "0"},
    )
    assert update_response.status_code == 302

    with app.app_context():
        conn = get_db()
        assert db.get_account(conn, _owner_id(app), account_id).balance == 200_000


def test_account_edit_unknown_account_404s(app, client: FlaskClient) -> None:
    assert client.get("/runway/accounts/999/edit").status_code == 404
    assert (
        client.post(
            "/runway/accounts/999/edit",
            data={"name": "X", "balance": "1.00", "penalty_tax_percent": "0"},
        ).status_code
        == 404
    )


def test_account_delete_removes_contribution(app, client: FlaskClient) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)
    account_id = _seed_account(app, "Cash", 706_000, 0)

    delete_response = client.post(f"/runway/accounts/{account_id}/delete")
    assert delete_response.status_code == 302

    response = client.get("/runway")
    body = response.get_data(as_text=True)
    assert "0.00 months" in body

    with app.app_context():
        conn = get_db()
        assert db.get_account(conn, _owner_id(app), account_id) is None


def test_account_delete_unknown_account_404s(app, client: FlaskClient) -> None:
    assert client.post("/runway/accounts/999/delete").status_code == 404


def test_account_create_negative_balance_shows_inline_error(
    app, client: FlaskClient
) -> None:
    response = client.post(
        "/runway/accounts",
        data={"name": "Cash", "balance": "-5.00", "penalty_tax_percent": "0"},
    )
    assert response.status_code == 400
    assert "error" in response.get_data(as_text=True).lower()


def test_account_create_out_of_range_percent_shows_inline_error(
    app, client: FlaskClient
) -> None:
    response = client.post(
        "/runway/accounts",
        data={"name": "401k", "balance": "10.00", "penalty_tax_percent": "150"},
    )
    assert response.status_code == 400
    assert "error" in response.get_data(as_text=True).lower()


def test_expenses_page_tags_essential_expenses_without_inline_toggle(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)
    _seed_expense(app, "Streaming", 1_500, "day_of_month", 31, essential=False)

    body = client.get("/expenses").get_data(as_text=True)

    assert body.count('class="tag"') == 1
    assert "toggle-essential" not in body


def test_expenses_page_groups_by_category_with_monthly_totals(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 145_000, "day_of_month", 1, category="Housing")
    _seed_expense(app, "Groceries", 15_000, "day_of_week", 5, category="Food")
    _seed_expense(app, "Streaming", 1_500, "day_of_month", 20)

    body = client.get("/expenses").get_data(as_text=True)

    assert body.index("Food") < body.index("Housing") < body.index("Uncategorized")
    assert "$650.00/mo" in body
    assert "$1,450.00/mo" in body
    assert "Day of Month" not in body


def test_expense_create_error_keeps_what_was_typed(app, client: FlaskClient) -> None:
    response = client.post(
        "/expenses",
        data={
            "name": "Gym",
            "amount": "45.00",
            "recurrence_type": "day_of_month",
            "recurrence_value": "",
            "category": "Health",
            "essential": "on",
        },
    )

    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert 'value="Gym"' in body
    assert 'value="45.00"' in body
    assert 'value="Health"' in body
    assert 'name="essential" checked' in body
    assert "Add expense</button>" in body


def test_expense_edit_error_stays_in_edit_mode_with_submitted_values(
    app, client: FlaskClient
) -> None:
    expense_id = _seed_expense(
        app, "Rent", 145_000, "day_of_month", 1, category="Housing"
    )

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "name": "Rent (new place)",
            "amount": "0",
            "recurrence_type": "day_of_month",
            "recurrence_value": "3",
            "category": "Housing",
        },
    )

    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "Edit Expense" in body
    assert "Save changes</button>" in body
    assert 'value="Rent (new place)"' in body
    assert 'value="3"' in body
    with app.app_context():
        conn = get_db()
        saved = db.get_expense(conn, _owner_id(app), expense_id)
    assert saved is not None and saved.name == "Rent" and saved.amount == 145_000


def test_expense_edit_form_shows_amount_with_cents(app, client: FlaskClient) -> None:
    expense_id = _seed_expense(app, "Fee", 5, "day_of_month", 1)

    body = client.get(f"/expenses/{expense_id}/edit").get_data(as_text=True)

    assert 'value="0.05"' in body


def test_expense_create_form_can_set_essential(app, client: FlaskClient) -> None:
    response = client.post(
        "/expenses",
        data={
            "name": "Rent",
            "amount": "2000.00",
            "recurrence_type": "day_of_month",
            "recurrence_value": "1",
            "essential": "on",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        conn = get_db()
        expenses = db.list_expenses(conn, _owner_id(app))
        assert expenses[0].essential is True


def test_expense_update_form_can_clear_essential(app, client: FlaskClient) -> None:
    expense_id = _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "name": "Rent",
            "amount": "2000.00",
            "recurrence_type": "day_of_month",
            "recurrence_value": "1",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        conn = get_db()
        assert db.get_expense(conn, _owner_id(app), expense_id).essential is False


def test_runway_page_has_no_essential_editing_controls(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)

    body = client.get("/runway").get_data(as_text=True)

    assert "essential-toggle" not in body
    assert "toggle-essential" not in body


def test_runway_essential_expenses_table_shows_frequency_and_total(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)

    body = client.get("/runway").get_data(as_text=True)

    assert "Rent" in body
    assert "Monthly, day 1" in body
    assert "Total (monthly)" in body
    assert "$2,000.00" in body or "$2000.00" in body


def test_runway_accounts_table_shows_total(app, client: FlaskClient) -> None:
    _seed_account(app, "Cash", 200_000, 0)
    _seed_account(app, "401k", 1_000_000, 30)

    body = client.get("/runway").get_data(as_text=True)

    assert "$12,000.00" in body or "$12000.00" in body


def test_runway_shows_spendable_after_penalty_and_uses_it_for_headline(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 100_000, "day_of_month", 1, essential=True)
    _seed_account(app, "Cash", 200_000, 0)
    _seed_account(app, "401k", 1_000_000, 30)

    body = client.get("/runway").get_data(as_text=True)

    # 401k spendable = $10,000 - 30% = $7,000; total spendable = $9,000
    assert "$7,000.00" in body
    assert "$9,000.00 spendable ÷ $1,000.00/mo essentials" in body
    assert "9.00 months" in body


def test_account_edit_error_stays_in_edit_mode_with_submitted_values(
    app, client: FlaskClient
) -> None:
    account_id = _seed_account(app, "Cash", 100_000, 0)

    response = client.post(
        f"/runway/accounts/{account_id}/edit",
        data={"name": "Cash (joint)", "balance": "-5.00", "penalty_tax_percent": "0"},
    )

    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "Edit Account" in body
    assert "Save changes</button>" in body
    assert 'value="Cash (joint)"' in body
    assert 'value="-5.00"' in body


def test_account_edit_form_prefills_balance_with_cents(app, client: FlaskClient) -> None:
    account_id = _seed_account(app, "Cash", 123_405, 15)

    body = client.get(f"/runway/accounts/{account_id}/edit").get_data(as_text=True)

    assert 'value="1234.05"' in body
    assert 'value="15"' in body


def test_debt_empty_state(app, client: FlaskClient) -> None:
    response = client.get("/debt")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "No debts recorded yet" in body


def test_debt_table_shows_rows_and_independent_totals(
    app, client: FlaskClient
) -> None:
    _seed_debt(
        app, "Visa", 200_000, interest_rate=20, minimum_payment=5_000, actual_payment=10_000
    )
    _seed_debt(
        app,
        "Car Loan",
        500_000,
        interest_rate=6,
        minimum_payment=15_000,
        actual_payment=0,
        kind="loan",
    )

    body = client.get("/debt").get_data(as_text=True)

    assert "Visa" in body
    assert "Car Loan" in body
    assert "$700,000.00" not in body  # sanity: not double counting
    assert "$7,000.00" in body  # totals.balance = 2000 + 5000
    assert "$200.00" in body  # totals.minimum_payment = 50 + 150
    # Monthly payments: Visa's $100 actual + Car Loan's $150 minimum (no actual set)
    assert "$250.00/mo in payments" in body


def test_debt_create_and_edit(app, client: FlaskClient) -> None:
    response = client.post(
        "/debt",
        data={
            "name": "Visa",
            "balance": "2000.00",
            "interest_rate": "20",
            "minimum_payment": "50.00",
            "actual_payment": "100.00",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        conn = get_db()
        accounts = db.list_debts(conn, _owner_id(app))
    assert len(accounts) == 1
    debt_id = accounts[0].id

    edit_response = client.get(f"/debt/{debt_id}/edit")
    assert edit_response.status_code == 200
    assert "2000.00" in edit_response.get_data(as_text=True)

    update_response = client.post(
        f"/debt/{debt_id}/edit",
        data={
            "name": "Visa",
            "balance": "1000.00",
            "interest_rate": "20",
            "minimum_payment": "50.00",
            "actual_payment": "50.00",
        },
    )
    assert update_response.status_code == 302

    with app.app_context():
        conn = get_db()
        updated = db.get_debt(conn, _owner_id(app), debt_id)
    assert updated.balance == 100_000
    assert updated.actual_payment == 5_000


def test_debt_edit_unknown_id_404s(app, client: FlaskClient) -> None:
    assert client.get("/debt/999/edit").status_code == 404
    assert (
        client.post(
            "/debt/999/edit",
            data={
                "name": "X",
                "balance": "1.00",
                "interest_rate": "0",
                "minimum_payment": "0",
                "actual_payment": "0",
            },
        ).status_code
        == 404
    )


def test_debt_create_negative_balance_shows_inline_error(
    app, client: FlaskClient
) -> None:
    response = client.post(
        "/debt",
        data={
            "name": "Visa",
            "balance": "-5.00",
            "interest_rate": "0",
            "minimum_payment": "0",
            "actual_payment": "0",
        },
    )
    assert response.status_code == 400
    assert "error" in response.get_data(as_text=True).lower()

    with app.app_context():
        conn = get_db()
        assert db.list_debts(conn, _owner_id(app)) == []


def test_debt_delete_removes_entry_and_updates_totals(
    app, client: FlaskClient
) -> None:
    debt_id = _seed_debt(app, "Visa", 200_000, minimum_payment=5_000)

    delete_response = client.post(f"/debt/{debt_id}/delete")
    assert delete_response.status_code == 302

    body = client.get("/debt").get_data(as_text=True)
    assert "No debts recorded yet" in body

    with app.app_context():
        conn = get_db()
        assert db.get_debt(conn, _owner_id(app), debt_id) is None


def test_debt_delete_unknown_id_404s(app, client: FlaskClient) -> None:
    assert client.post("/debt/999/delete").status_code == 404


def test_debt_payoff_time_display_states(app, client: FlaskClient) -> None:
    _seed_debt(
        app, "Visa", 200_000, interest_rate=20, minimum_payment=5_000, actual_payment=10_000
    )
    _seed_debt(app, "Paid Off Card", 0, minimum_payment=2_000)
    _seed_debt(
        app, "Maxed Card", 100_000, interest_rate=24, minimum_payment=0, actual_payment=0
    )

    body = client.get("/debt").get_data(as_text=True)

    assert "25 months" in body
    assert "Paid off" in body
    assert "Never at this rate" in body


def test_debt_shows_usage_percent_and_credit_limit_total(
    app, client: FlaskClient
) -> None:
    _seed_debt(app, "Visa", 30_000, credit_limit=100_000)
    _seed_debt(app, "Untracked Limit", 50_000, credit_limit=0)

    body = client.get("/debt").get_data(as_text=True)

    assert "30.0% of $1,000.00" in body  # Visa: 30000/100000
    assert "N/A" not in body  # a card with no limit just shows no usage line
    # Card usage counts only cards with a limit: 30000/100000, not 80000/100000
    assert "30.0% of limit used" in body


def test_debt_create_and_edit_with_credit_limit(
    app, client: FlaskClient
) -> None:
    client.post(
        "/debt",
        data={
            "name": "Visa",
            "balance": "300.00",
            "interest_rate": "0",
            "minimum_payment": "0",
            "actual_payment": "0",
            "credit_limit": "1000.00",
        },
    )

    with app.app_context():
        conn = get_db()
        account = db.list_debts(conn, _owner_id(app))[0]
    assert account.credit_limit == 100_000

    client.post(
        f"/debt/{account.id}/edit",
        data={
            "name": "Visa",
            "balance": "300.00",
            "interest_rate": "0",
            "minimum_payment": "0",
            "actual_payment": "0",
            "credit_limit": "1500.00",
        },
    )

    with app.app_context():
        conn = get_db()
        updated = db.get_debt(conn, _owner_id(app), account.id)
    assert updated.credit_limit == 150_000


def test_debt_page_groups_cards_and_loans_with_card_usage(
    app, client: FlaskClient
) -> None:
    _seed_debt(app, "Visa", 345_012, interest_rate=24.99, credit_limit=1_500_000)
    _seed_debt(app, "Student loan", 1_823_400, interest_rate=5.5, kind="loan")

    body = client.get("/debt").get_data(as_text=True)

    assert body.index("Credit cards") < body.index("Visa")
    assert body.index("Visa") < body.index("Loans") < body.index("Student loan")
    # The loan's balance doesn't inflate card usage (was 144.6% before)
    assert "23.0% of limit used" in body
    assert "144.6%" not in body


def test_debt_loan_with_credit_limit_is_rejected(app, client: FlaskClient) -> None:
    response = client.post(
        "/debt",
        data={
            "kind": "loan",
            "name": "Car loan",
            "balance": "5000.00",
            "credit_limit": "1000.00",
        },
    )

    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "credit limit" in body
    assert 'value="Car loan"' in body
    assert '<option value="loan" selected>' in body


def test_debt_create_loan(app, client: FlaskClient) -> None:
    response = client.post(
        "/debt",
        data={"kind": "loan", "name": "Car loan", "balance": "5000.00"},
    )

    assert response.status_code == 302
    with app.app_context():
        conn = get_db()
        (debt,) = db.list_debts(conn, _owner_id(app))
    assert debt.kind == "loan"
    assert debt.credit_limit == 0


def test_debt_edit_error_stays_in_edit_mode_with_submitted_values(
    app, client: FlaskClient
) -> None:
    debt_id = _seed_debt(app, "Visa", 100_000, interest_rate=20)

    response = client.post(
        f"/debt/{debt_id}/edit",
        data={"kind": "credit_card", "name": "Visa Signature", "balance": "-1.00"},
    )

    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "Edit Card or Loan" in body
    assert "Save changes</button>" in body
    assert 'value="Visa Signature"' in body


def test_old_credit_cards_url_redirects_to_debt(app, client: FlaskClient) -> None:
    response = client.get("/credit-cards")

    assert response.status_code == 301
    assert response.headers["Location"] == "/debt"
