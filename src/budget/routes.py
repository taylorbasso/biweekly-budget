from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from budget import db
from budget.app import get_db
from budget.calculations import compute_breakdown, compute_leftover, occurrences_in_cycle
from budget.cycles import resolve_cycle
from budget.models import PaySchedule, RecurringExpense, ValidationError

bp = Blueprint("budget", __name__)


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
    return RecurringExpense(
        id=expense_id,
        name=name,
        amount=amount,
        recurrence_type=recurrence_type,
        recurrence_value=recurrence_value,
        category=category,
        recurrence_anchor=recurrence_anchor,
    )


@bp.route("/")
def leftover() -> str:
    conn = get_db()
    pay_schedule = db.get_pay_schedule(conn)
    if pay_schedule is None:
        return render_template("leftover.html", pay_schedule=None, result=None)

    reference_date = _parse_reference_date()
    cycle = resolve_cycle(pay_schedule, reference_date)
    expenses = db.list_expenses(conn)
    occurrences = occurrences_in_cycle(expenses, cycle)
    result = compute_leftover(pay_schedule, occurrences, cycle)
    return render_template("leftover.html", pay_schedule=pay_schedule, result=result)


@bp.route("/pay-schedule", methods=["GET", "POST"])
def pay_schedule() -> ResponseReturnValue:
    conn = get_db()
    if request.method == "GET":
        return render_template(
            "pay_schedule.html", pay_schedule=db.get_pay_schedule(conn), error=None
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

    db.set_pay_schedule(conn, schedule)
    return redirect(url_for("budget.pay_schedule"))


@bp.route("/breakdown")
def breakdown() -> str:
    conn = get_db()
    pay_schedule = db.get_pay_schedule(conn)
    if pay_schedule is None:
        return render_template("breakdown.html", pay_schedule=None, result=None)

    reference_date = _parse_reference_date()
    cycle = resolve_cycle(pay_schedule, reference_date)
    expenses = db.list_expenses(conn)
    occurrences = occurrences_in_cycle(expenses, cycle)
    result = compute_breakdown(cycle, occurrences)
    return render_template("breakdown.html", pay_schedule=pay_schedule, result=result)


@bp.route("/expenses")
def expenses_list() -> str:
    conn = get_db()
    return render_template("expenses_list.html", expenses=db.list_expenses(conn))


@bp.route("/expenses/new", methods=["GET"])
def expense_new() -> str:
    return render_template(
        "expense_form.html", expense=None, error=None, action="/expenses"
    )


@bp.route("/expenses", methods=["POST"])
def expense_create() -> ResponseReturnValue:
    try:
        expense = _expense_from_form(None)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "expense_form.html", expense=None, error=str(exc), action="/expenses"
            ),
            400,
        )
    conn = get_db()
    db.create_expense(conn, expense)
    return redirect(url_for("budget.expenses_list"))


@bp.route("/expenses/<int:expense_id>/edit", methods=["GET"])
def expense_edit(expense_id: int) -> str:
    conn = get_db()
    expense = db.get_expense(conn, expense_id)
    if expense is None:
        abort(404)
    return render_template(
        "expense_form.html",
        expense=expense,
        error=None,
        action=f"/expenses/{expense_id}/edit",
    )


@bp.route("/expenses/<int:expense_id>/edit", methods=["POST"])
def expense_update(expense_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_expense(conn, expense_id) is None:
        abort(404)
    try:
        expense = _expense_from_form(expense_id)
    except (ValueError, ValidationError) as exc:
        return (
            render_template(
                "expense_form.html",
                expense=None,
                error=str(exc),
                action=f"/expenses/{expense_id}/edit",
            ),
            400,
        )
    db.update_expense(conn, expense_id, expense)
    return redirect(url_for("budget.expenses_list"))


@bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def expense_delete(expense_id: int) -> ResponseReturnValue:
    conn = get_db()
    if db.get_expense(conn, expense_id) is None:
        abort(404)
    db.delete_expense(conn, expense_id)
    return redirect(url_for("budget.expenses_list"))
