from __future__ import annotations

from datetime import date

from flask.testing import FlaskClient

from budget import db
from budget.app import get_db
from budget.models import Account, CreditAccount, PaySchedule, RecurringExpense


def _seed_pay_schedule(app, anchor_date: date, amount: int) -> None:
    with app.app_context():
        conn = get_db()
        db.set_pay_schedule(conn, PaySchedule(anchor_date=anchor_date, amount=amount))


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
            Account(
                id=None,
                name=name,
                balance=balance,
                penalty_tax_percent=penalty_tax_percent,
            ),
        )


def _seed_credit_account(
    app,
    name: str,
    balance: int,
    interest_rate: float = 0,
    minimum_payment: int = 0,
    actual_payment: int = 0,
    credit_limit: int = 0,
) -> int:
    with app.app_context():
        conn = get_db()
        return db.create_credit_account(
            conn,
            CreditAccount(
                id=None,
                name=name,
                balance=balance,
                interest_rate=interest_rate,
                minimum_payment=minimum_payment,
                actual_payment=actual_payment,
                credit_limit=credit_limit,
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
    assert "<svg" not in body


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


def test_annual_cost_page_empty_state_shows_zero_grand_total(
    app, client: FlaskClient
) -> None:
    response = client.get("/annual-cost")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "No expenses recorded" in body
    assert "$0.00" in body


def test_toggle_essential_persists_and_redirects(app, client: FlaskClient) -> None:
    expense_id = _seed_expense(app, "Rent", 200_000, "day_of_month", 1)

    response = client.post(f"/expenses/{expense_id}/toggle-essential")
    assert response.status_code == 302

    with app.app_context():
        conn = get_db()
        assert db.get_expense(conn, expense_id).essential is True

    client.post(f"/expenses/{expense_id}/toggle-essential")
    with app.app_context():
        conn = get_db()
        assert db.get_expense(conn, expense_id).essential is False


def test_toggle_essential_unknown_expense_404s(app, client: FlaskClient) -> None:
    response = client.post("/expenses/999/toggle-essential")
    assert response.status_code == 404


def test_runway_single_account_matches_quickstart_scenario_a(
    app, client: FlaskClient
) -> None:
    expense_id = _seed_expense(app, "Rent", 200_000, "day_of_month", 1)
    client.post(f"/expenses/{expense_id}/toggle-essential")
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
    expense_id = _seed_expense(app, "Rent", 200_000, "day_of_month", 1)
    client.post(f"/expenses/{expense_id}/toggle-essential")
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
    expense_id = _seed_expense(app, "Rent", 200_000, "day_of_month", 1)
    client.post(f"/expenses/{expense_id}/toggle-essential")

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
        assert db.get_account(conn, account_id).balance == 200_000


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
    expense_id = _seed_expense(app, "Rent", 200_000, "day_of_month", 1)
    client.post(f"/expenses/{expense_id}/toggle-essential")
    account_id = _seed_account(app, "Cash", 706_000, 0)

    delete_response = client.post(f"/runway/accounts/{account_id}/delete")
    assert delete_response.status_code == 302

    response = client.get("/runway")
    body = response.get_data(as_text=True)
    assert "0.00 months" in body

    with app.app_context():
        conn = get_db()
        assert db.get_account(conn, account_id) is None


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


def test_toggle_essential_redirects_to_expenses_list(app, client: FlaskClient) -> None:
    expense_id = _seed_expense(app, "Rent", 200_000, "day_of_month", 1)

    response = client.post(f"/expenses/{expense_id}/toggle-essential")

    assert response.status_code == 302
    assert response.headers["Location"] == "/expenses"


def test_expenses_page_shows_essential_checkbox_state(
    app, client: FlaskClient
) -> None:
    _seed_expense(app, "Rent", 200_000, "day_of_month", 1, essential=True)
    _seed_expense(app, "Streaming", 1_500, "day_of_month", 31, essential=False)

    body = client.get("/expenses").get_data(as_text=True)

    assert "essential-toggle" in body
    assert 'action="/expenses/1/toggle-essential"' in body


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
        expenses = db.list_expenses(conn)
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
        assert db.get_expense(conn, expense_id).essential is False


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
    assert "Monthly (day 1)" in body
    assert "Total (monthly)" in body
    assert "$2,000.00" in body or "$2000.00" in body


def test_runway_accounts_table_shows_total(app, client: FlaskClient) -> None:
    _seed_account(app, "Cash", 200_000, 0)
    _seed_account(app, "401k", 1_000_000, 30)

    body = client.get("/runway").get_data(as_text=True)

    assert "$12,000.00" in body or "$12000.00" in body


def test_credit_cards_empty_state(app, client: FlaskClient) -> None:
    response = client.get("/credit-cards")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "No credit cards or loans recorded" in body


def test_credit_cards_table_shows_rows_and_independent_totals(
    app, client: FlaskClient
) -> None:
    _seed_credit_account(
        app, "Visa", 200_000, interest_rate=20, minimum_payment=5_000, actual_payment=10_000
    )
    _seed_credit_account(
        app, "Car Loan", 500_000, interest_rate=6, minimum_payment=15_000, actual_payment=0
    )

    body = client.get("/credit-cards").get_data(as_text=True)

    assert "Visa" in body
    assert "Car Loan" in body
    assert "$700,000.00" not in body  # sanity: not double counting
    assert "$7,000.00" in body  # totals.balance = 2000 + 5000
    assert "$200.00" in body  # totals.minimum_payment = 50 + 150
    assert "$100.00" in body  # totals.actual_payment = 100 + 0


def test_credit_cards_create_and_edit(app, client: FlaskClient) -> None:
    response = client.post(
        "/credit-cards",
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
        accounts = db.list_credit_accounts(conn)
    assert len(accounts) == 1
    credit_account_id = accounts[0].id

    edit_response = client.get(f"/credit-cards/{credit_account_id}/edit")
    assert edit_response.status_code == 200
    assert "2000.00" in edit_response.get_data(as_text=True)

    update_response = client.post(
        f"/credit-cards/{credit_account_id}/edit",
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
        updated = db.get_credit_account(conn, credit_account_id)
    assert updated.balance == 100_000
    assert updated.actual_payment == 5_000


def test_credit_account_edit_unknown_id_404s(app, client: FlaskClient) -> None:
    assert client.get("/credit-cards/999/edit").status_code == 404
    assert (
        client.post(
            "/credit-cards/999/edit",
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


def test_credit_account_create_negative_balance_shows_inline_error(
    app, client: FlaskClient
) -> None:
    response = client.post(
        "/credit-cards",
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
        assert db.list_credit_accounts(conn) == []


def test_credit_account_delete_removes_entry_and_updates_totals(
    app, client: FlaskClient
) -> None:
    credit_account_id = _seed_credit_account(app, "Visa", 200_000, minimum_payment=5_000)

    delete_response = client.post(f"/credit-cards/{credit_account_id}/delete")
    assert delete_response.status_code == 302

    body = client.get("/credit-cards").get_data(as_text=True)
    assert "No credit cards or loans recorded" in body

    with app.app_context():
        conn = get_db()
        assert db.get_credit_account(conn, credit_account_id) is None


def test_credit_account_delete_unknown_id_404s(app, client: FlaskClient) -> None:
    assert client.post("/credit-cards/999/delete").status_code == 404


def test_credit_cards_payoff_time_display_states(app, client: FlaskClient) -> None:
    _seed_credit_account(
        app, "Visa", 200_000, interest_rate=20, minimum_payment=5_000, actual_payment=10_000
    )
    _seed_credit_account(app, "Paid Off Card", 0, minimum_payment=2_000)
    _seed_credit_account(
        app, "Maxed Card", 100_000, interest_rate=24, minimum_payment=0, actual_payment=0
    )

    body = client.get("/credit-cards").get_data(as_text=True)

    assert "25 months" in body
    assert "Paid off" in body
    assert "Never at this rate" in body


def test_credit_cards_shows_usage_percent_and_credit_limit_total(
    app, client: FlaskClient
) -> None:
    _seed_credit_account(app, "Visa", 30_000, credit_limit=100_000)
    _seed_credit_account(app, "Untracked Limit", 50_000, credit_limit=0)

    body = client.get("/credit-cards").get_data(as_text=True)

    assert "30.0%" in body  # Visa: 30000/100000
    assert "N/A" in body  # Untracked Limit has no credit_limit set
    assert "$1,000.00" in body  # totals.credit_limit


def test_credit_account_create_and_edit_with_credit_limit(
    app, client: FlaskClient
) -> None:
    client.post(
        "/credit-cards",
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
        account = db.list_credit_accounts(conn)[0]
    assert account.credit_limit == 100_000

    client.post(
        f"/credit-cards/{account.id}/edit",
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
        updated = db.get_credit_account(conn, account.id)
    assert updated.credit_limit == 150_000
