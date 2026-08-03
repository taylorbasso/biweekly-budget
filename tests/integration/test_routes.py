from __future__ import annotations

from datetime import date

from flask.testing import FlaskClient

from budget import db
from budget.app import get_db
from budget.models import PaySchedule, RecurringExpense


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
) -> None:
    with app.app_context():
        conn = get_db()
        db.create_expense(
            conn,
            RecurringExpense(
                id=None,
                name=name,
                amount=amount,
                recurrence_type=recurrence_type,
                recurrence_value=recurrence_value,
                category=category,
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
