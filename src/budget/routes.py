from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user

from budget import db
from budget.app import get_db
from budget.auth import login_manager
from budget.calculations import (
    compute_annual_cost_breakdown,
    compute_breakdown,
    compute_credit_cards,
    compute_leftover,
    compute_runway,
    group_expenses_by_category,
    monthly_equivalent,
    occurrences_in_cycle,
)
from budget.charts import build_chart
from budget.cycles import resolve_cycle, upcoming_cycles
from budget.models import (
    Account,
    CreditAccount,
    PaySchedule,
    RecurringExpense,
    ValidationError,
)

bp = Blueprint("budget", __name__)


@bp.before_request
def _require_login() -> ResponseReturnValue | None:
    """Every route in this blueprint requires a signed-in account (Principle VI)."""
    if not current_user.is_authenticated:
        return login_manager.unauthorized()  # type: ignore[no-any-return]
    return None


def _user_id() -> int:
    return int(current_user.id)


CYCLE_OPTIONS_COUNT = 10


def _existing_categories(conn: db.Connection) -> list[str]:
    categories = {
        expense.category for expense in db.list_expenses(conn, _user_id()) if expense.category
    }
    return sorted(categories)


def _parse_reference_date() -> date:
    raw = request.args.get("date")
    if raw is None:
        return date.today()
    return date.fromisoformat(raw)


def _parse_dollars(raw: str) -> int:
    try:
        dollars = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("amount must be a valid number") from exc
    return int((dollars * 100).to_integral_value())


def _expense_from_form(expense_id: int | None) -> RecurringExpense:
    name = request.form.get("name", "")
    amount = _parse_dollars(request.form.get("amount", ""))
    recurrence_type = request.form.get("recurrence_type", "")
    recurrence_value_raw = request.form.get("recurrence_value", "").strip()
    recurrence_value = int(recurrence_value_raw) if recurrence_value_raw else 0
    recurrence_anchor_raw = request.form.get("recurrence_anchor", "").strip()
    recurrence_anchor = (
        date.fromisoformat(recurrence_anchor_raw) if recurrence_anchor_raw else None
    )
    category = request.form.get("category", "").strip() or None
    essential = request.form.get("essential") == "on"
    return RecurringExpense(
        id=expense_id,
        name=name,
        amount=amount,
        recurrence_type=recurrence_type,
        recurrence_value=recurrence_value,
        category=category,
        recurrence_anchor=recurrence_anchor,
        essential=essential,
    )


def _expense_form_values(expense: RecurringExpense | None) -> dict[str, str | bool]:
    """Field values for expense_form.html, from a saved expense (or blank for a new one)."""
    if expense is None:
        return {
            "name": "",
            "amount": "",
            "recurrence_type": "day_of_month",
            "recurrence_value": "",
            "recurrence_anchor": "",
            "category": "",
            "essential": False,
        }
    return {
        "name": expense.name,
        "amount": f"{expense.amount // 100}.{expense.amount % 100:02d}",
        "recurrence_type": expense.recurrence_type,
        "recurrence_value": str(expense.recurrence_value),
        "recurrence_anchor": (
            expense.recurrence_anchor.isoformat() if expense.recurrence_anchor else ""
        ),
        "category": expense.category or "",
        "essential": expense.essential,
    }


def _expense_form_values_from_request() -> dict[str, str | bool]:
    """What the user just submitted, so a rejected form comes back as they typed it."""
    fields = (
        "name",
        "amount",
        "recurrence_type",
        "recurrence_value",
        "recurrence_anchor",
        "category",
    )
    values: dict[str, str | bool] = {
        field: request.form.get(field, "") for field in fields
    }
    values["essential"] = request.form.get("essential") == "on"
    return values


@bp.route("/")
def leftover() -> str:
    conn = get_db()
    pay_schedule = db.get_pay_schedule(conn, _user_id())
    if pay_schedule is None:
        return render_template("leftover.html", pay_schedule=None, result=None)

    reference_date = _parse_reference_date()
    cycle = resolve_cycle(pay_schedule, reference_date)
    current_cycle = resolve_cycle(pay_schedule, date.today())
    cycle_options = upcoming_cycles(current_cycle, CYCLE_OPTIONS_COUNT)
    expenses = db.list_expenses(conn, _user_id())
    occurrences = occurrences_in_cycle(expenses, cycle)
    result = compute_leftover(pay_schedule, occurrences, cycle, reference_date)
    breakdown = compute_breakdown(cycle, occurrences)
    chart = build_chart(result.pay_amount, breakdown.totals, result.leftover_amount)
    return render_template(
        "leftover.html",
        pay_schedule=pay_schedule,
        result=result,
        chart=chart,
        category_items=breakdown.items,
        today=reference_date,
        cycle_options=cycle_options,
        selected_start=cycle.start_date,
    )


@bp.route("/pay-schedule", methods=["GET", "POST"])
def pay_schedule() -> ResponseReturnValue:
    conn = get_db()
    if request.method == "GET":
        return render_template(
            "pay_schedule.html", pay_schedule=db.get_pay_schedule(conn, _user_id()), error=None
        )

    try:
        anchor_date = date.fromisoformat(request.form.get("anchor_date", ""))
        amount = _parse_dollars(request.form.get("amount", ""))
        schedule = PaySchedule(anchor_date=anchor_date, amount=amount)
    except (ValueError, ValidationError) as exc:
        return (
            render_template("pay_schedule.html", pay_schedule=None, error=str(exc)),
            400,
        )

    db.set_pay_schedule(conn, _user_id(), schedule)
    return redirect(url_for("budget.pay_schedule"))


@bp.route("/expenses")
def expenses_list() -> str:
    conn = get_db()
    groups = group_expenses_by_category(db.list_expenses(conn, _user_id()))
    return render_template("expenses_list.html", groups=groups)


@bp.route("/annual-cost")
def annual_cost() -> str:
    conn = get_db()
    expenses = db.list_expenses(conn, _user_id())
    breakdown = compute_annual_cost_breakdown(expenses)
    return render_template("annual_cost.html", breakdown=breakdown)


def _account_from_form(account_id: int | None) -> Account:
    name = request.form.get("name", "")
    balance = _parse_dollars(request.form.get("balance", ""))
    percent_raw = request.form.get("penalty_tax_percent", "").strip()
    penalty_tax_percent = int(percent_raw) if percent_raw else 0
    return Account(
        id=account_id,
        name=name,
        balance=balance,
        penalty_tax_percent=penalty_tax_percent,
    )


@bp.route("/runway")
def runway() -> str:
    conn = get_db()
    expenses = db.list_expenses(conn, _user_id())
    accounts = db.list_accounts(conn, _user_id())
    result = compute_runway(expenses, accounts)
    essential_rows = [
        (expense, round(monthly_equivalent(expense)))
        for expense in expenses
        if expense.essential
    ]
    total_account_balance = sum((account.balance for account in accounts), 0)
    total_monthly_burn = round(result.monthly_essential_burn)
    return render_template(
        "runway.html",
        essential_rows=essential_rows,
        accounts=accounts,
        result=result,
        total_account_balance=total_account_balance,
        total_monthly_burn=total_monthly_burn,
    )


@bp.route("/runway/accounts/new", methods=["GET"])
def account_new() -> str:
    return render_template(
        "account_form.html", account=None, error=None, action="/runway/accounts"
    )


@bp.route("/runway/accounts", methods=["POST"])
def account_create() -> ResponseReturnValue:
    try:
        account = _account_from_form(None)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "account_form.html",
                account=None,
                error=str(exc),
                action="/runway/accounts",
            ),
            400,
        )
    conn = get_db()
    db.create_account(conn, _user_id(), account)
    return redirect(url_for("budget.runway"))


@bp.route("/runway/accounts/<int:account_id>/edit", methods=["GET"])
def account_edit(account_id: int) -> str:
    conn = get_db()
    account = db.get_account(conn, _user_id(), account_id)
    if account is None:
        abort(404)
    return render_template(
        "account_form.html",
        account=account,
        error=None,
        action=f"/runway/accounts/{account_id}/edit",
    )


@bp.route("/runway/accounts/<int:account_id>/edit", methods=["POST"])
def account_update(account_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_account(conn, _user_id(), account_id) is None:
        abort(404)
    try:
        account = _account_from_form(account_id)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "account_form.html",
                account=None,
                error=str(exc),
                action=f"/runway/accounts/{account_id}/edit",
            ),
            400,
        )
    db.update_account(conn, _user_id(), account_id, account)
    return redirect(url_for("budget.runway"))


@bp.route("/runway/accounts/<int:account_id>/delete", methods=["POST"])
def account_delete(account_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_account(conn, _user_id(), account_id) is None:
        abort(404)
    db.delete_account(conn, _user_id(), account_id)
    return redirect(url_for("budget.runway"))


def _credit_account_from_form(credit_account_id: int | None) -> CreditAccount:
    name = request.form.get("name", "")
    balance = _parse_dollars(request.form.get("balance", ""))
    interest_rate_raw = request.form.get("interest_rate", "").strip()
    interest_rate = float(interest_rate_raw) if interest_rate_raw else 0.0
    minimum_payment = _parse_dollars(request.form.get("minimum_payment", "") or "0")
    actual_payment_raw = request.form.get("actual_payment", "").strip()
    actual_payment = _parse_dollars(actual_payment_raw) if actual_payment_raw else 0
    credit_limit_raw = request.form.get("credit_limit", "").strip()
    credit_limit = _parse_dollars(credit_limit_raw) if credit_limit_raw else 0
    return CreditAccount(
        id=credit_account_id,
        name=name,
        balance=balance,
        interest_rate=interest_rate,
        minimum_payment=minimum_payment,
        actual_payment=actual_payment,
        credit_limit=credit_limit,
    )


@bp.route("/credit-cards")
def credit_cards() -> str:
    conn = get_db()
    accounts = db.list_credit_accounts(conn, _user_id())
    rows, totals = compute_credit_cards(accounts)
    return render_template("credit_cards.html", rows=rows, totals=totals)


@bp.route("/credit-cards/new", methods=["GET"])
def credit_account_new() -> str:
    return render_template(
        "credit_account_form.html", account=None, error=None, action="/credit-cards"
    )


@bp.route("/credit-cards", methods=["POST"])
def credit_account_create() -> ResponseReturnValue:
    try:
        account = _credit_account_from_form(None)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "credit_account_form.html",
                account=None,
                error=str(exc),
                action="/credit-cards",
            ),
            400,
        )
    conn = get_db()
    db.create_credit_account(conn, _user_id(), account)
    return redirect(url_for("budget.credit_cards"))


@bp.route("/credit-cards/<int:credit_account_id>/edit", methods=["GET"])
def credit_account_edit(credit_account_id: int) -> str:
    conn = get_db()
    account = db.get_credit_account(conn, _user_id(), credit_account_id)
    if account is None:
        abort(404)
    return render_template(
        "credit_account_form.html",
        account=account,
        error=None,
        action=f"/credit-cards/{credit_account_id}/edit",
    )


@bp.route("/credit-cards/<int:credit_account_id>/edit", methods=["POST"])
def credit_account_update(credit_account_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_credit_account(conn, _user_id(), credit_account_id) is None:
        abort(404)
    try:
        account = _credit_account_from_form(credit_account_id)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "credit_account_form.html",
                account=None,
                error=str(exc),
                action=f"/credit-cards/{credit_account_id}/edit",
            ),
            400,
        )
    db.update_credit_account(conn, _user_id(), credit_account_id, account)
    return redirect(url_for("budget.credit_cards"))


@bp.route("/credit-cards/<int:credit_account_id>/delete", methods=["POST"])
def credit_account_delete(credit_account_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_credit_account(conn, _user_id(), credit_account_id) is None:
        abort(404)
    db.delete_credit_account(conn, _user_id(), credit_account_id)
    return redirect(url_for("budget.credit_cards"))


@bp.route("/expenses/new", methods=["GET"])
def expense_new() -> str:
    conn = get_db()
    return render_template(
        "expense_form.html",
        values=_expense_form_values(None),
        error=None,
        action="/expenses",
        categories=_existing_categories(conn),
    )


@bp.route("/expenses", methods=["POST"])
def expense_create() -> ResponseReturnValue:
    conn = get_db()
    try:
        expense = _expense_from_form(None)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "expense_form.html",
                values=_expense_form_values_from_request(),
                error=str(exc),
                action="/expenses",
                categories=_existing_categories(conn),
            ),
            400,
        )
    db.create_expense(conn, _user_id(), expense)
    return redirect(url_for("budget.expenses_list"))


@bp.route("/expenses/<int:expense_id>/edit", methods=["GET"])
def expense_edit(expense_id: int) -> str:
    conn = get_db()
    expense = db.get_expense(conn, _user_id(), expense_id)
    if expense is None:
        abort(404)
    return render_template(
        "expense_form.html",
        values=_expense_form_values(expense),
        error=None,
        action=f"/expenses/{expense_id}/edit",
        categories=_existing_categories(conn),
    )


@bp.route("/expenses/<int:expense_id>/edit", methods=["POST"])
def expense_update(expense_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_expense(conn, _user_id(), expense_id) is None:
        abort(404)
    try:
        expense = _expense_from_form(expense_id)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "expense_form.html",
                values=_expense_form_values_from_request(),
                error=str(exc),
                action=f"/expenses/{expense_id}/edit",
                categories=_existing_categories(conn),
            ),
            400,
        )
    db.update_expense(conn, _user_id(), expense_id, expense)
    return redirect(url_for("budget.expenses_list"))


@bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def expense_delete(expense_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_expense(conn, _user_id(), expense_id) is None:
        abort(404)
    db.delete_expense(conn, _user_id(), expense_id)
    return redirect(url_for("budget.expenses_list"))
