from __future__ import annotations

from datetime import date, timedelta

import pytest

from budget.calculations import (
    UNCATEGORIZED,
    compute_breakdown,
    compute_leftover,
    occurrences_in_cycle,
)
from budget.cycles import Cycle
from budget.models import PaySchedule, RecurringExpense, ValidationError


def _expense(
    name: str,
    amount: int,
    recurrence_type: str,
    recurrence_value: int,
    category: str | None = None,
    expense_id: int | None = 1,
    recurrence_anchor: date | None = None,
) -> RecurringExpense:
    return RecurringExpense(
        id=expense_id,
        name=name,
        amount=amount,
        recurrence_type=recurrence_type,
        recurrence_value=recurrence_value,
        category=category,
        recurrence_anchor=recurrence_anchor,
    )


def test_day_of_month_clamps_31st_in_30_day_month() -> None:
    cycle = Cycle(
        start_date=date(2026, 9, 17),
        end_date=date(2026, 9, 30),
        next_pay_date=date(2026, 10, 1),
    )
    expense = _expense("Streaming", 1500, "day_of_month", 31)
    occurrences = occurrences_in_cycle([expense], cycle)
    assert len(occurrences) == 1
    assert occurrences[0].due_date == date(2026, 9, 30)


def test_day_of_month_clamps_29_30_31_in_february_non_leap_year() -> None:
    cycle_excluding_28th = Cycle(
        start_date=date(2027, 2, 14),
        end_date=date(2027, 2, 27),
        next_pay_date=date(2027, 2, 28),
    )
    for recurrence_value in (29, 30, 31):
        expense = _expense("Bill", 1000, "day_of_month", recurrence_value)
        occurrences = occurrences_in_cycle([expense], cycle_excluding_28th)
        assert len(occurrences) == 0

    cycle_including_28th = Cycle(
        start_date=date(2027, 2, 21),
        end_date=date(2027, 3, 6),
        next_pay_date=date(2027, 3, 7),
    )
    for recurrence_value in (29, 30, 31):
        expense = _expense("Bill", 1000, "day_of_month", recurrence_value)
        occurrences = occurrences_in_cycle([expense], cycle_including_28th)
        assert len(occurrences) == 1
        assert occurrences[0].due_date == date(2027, 2, 28)


def test_day_of_month_clamps_29th_in_leap_year_february() -> None:
    cycle = Cycle(
        start_date=date(2028, 2, 15),
        end_date=date(2028, 2, 28),
        next_pay_date=date(2028, 2, 29),
    )
    expense = _expense("Bill", 1000, "day_of_month", 29)
    occurrences = occurrences_in_cycle([expense], cycle)
    assert len(occurrences) == 0

    cycle_including_29th = Cycle(
        start_date=date(2028, 2, 29),
        end_date=date(2028, 3, 13),
        next_pay_date=date(2028, 3, 14),
    )
    occurrences = occurrences_in_cycle([expense], cycle_including_29th)
    assert len(occurrences) == 1
    assert occurrences[0].due_date == date(2028, 2, 29)


def test_day_of_week_yields_exactly_two_occurrences_per_cycle() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    expense = _expense("Investment transfer", 10000, "day_of_week", 4)  # Friday
    occurrences = occurrences_in_cycle([expense], cycle)
    assert len(occurrences) == 2
    assert [o.due_date for o in occurrences] == [date(2026, 7, 31), date(2026, 8, 7)]


def test_expense_with_no_category_is_uncategorized() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    expense = _expense("Streaming", 1500, "day_of_month", 31, category=None)
    occurrences = occurrences_in_cycle([expense], cycle)
    assert occurrences[0].category == UNCATEGORIZED


def test_occurrence_exactly_on_cycle_start_date_is_included() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    schedule = PaySchedule(anchor_date=date(2026, 7, 31), amount=200_000)
    expense = _expense("Rent", 120_000, "day_of_month", 31)  # due July 31
    occurrences = occurrences_in_cycle([expense], cycle)
    result = compute_leftover(schedule, occurrences, cycle)
    assert result.total_expenses == 120_000
    assert result.leftover_amount == 80_000


def test_occurrence_exactly_on_cycle_end_date_is_included() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    schedule = PaySchedule(anchor_date=date(2026, 7, 31), amount=200_000)
    expense = _expense("Card due", 5_000, "day_of_month", 13)  # due Aug 13
    occurrences = occurrences_in_cycle([expense], cycle)
    result = compute_leftover(schedule, occurrences, cycle)
    assert result.total_expenses == 5_000
    assert len(result.occurrences) == 1
    assert result.occurrences[0].due_date == date(2026, 8, 13)


def test_occurrence_exactly_on_next_pay_date_is_excluded() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    schedule = PaySchedule(anchor_date=date(2026, 7, 31), amount=200_000)
    expense = _expense("Due on next pay date", 5_000, "day_of_month", 14)  # Aug 14
    occurrences = occurrences_in_cycle([expense], cycle)
    result = compute_leftover(schedule, occurrences, cycle)
    assert result.total_expenses == 0
    assert result.occurrences == []
    assert result.leftover_amount == 200_000


def test_uncategorized_expense_grouped_under_catchall_category() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    schedule = PaySchedule(anchor_date=date(2026, 7, 31), amount=200_000)
    expenses = [
        _expense("Rent", 120_000, "day_of_month", 1, category="Housing", expense_id=1),
        _expense(
            "Investment",
            10_000,
            "day_of_week",
            4,
            category="Investments",
            expense_id=2,
        ),
        _expense("Streaming", 1_500, "day_of_month", 31, category=None, expense_id=3),
    ]
    occurrences = occurrences_in_cycle(expenses, cycle)
    breakdown = compute_breakdown(cycle, occurrences)
    totals = dict(breakdown.totals)
    assert totals["Housing"] == 120_000
    assert totals["Investments"] == 20_000  # two Friday occurrences
    assert totals[UNCATEGORIZED] == 1_500

    leftover = compute_leftover(schedule, occurrences, cycle)
    assert sum(amount for _, amount in breakdown.totals) == leftover.total_expenses


def test_biweekly_occurrence_exactly_on_cycle_start_date() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    expense = _expense(
        "Mortgage",
        150_000,
        "biweekly",
        0,
        recurrence_anchor=date(2026, 7, 31),
    )
    occurrences = occurrences_in_cycle([expense], cycle)
    assert len(occurrences) == 1
    assert occurrences[0].due_date == date(2026, 7, 31)


def test_biweekly_occurrence_exactly_on_cycle_end_date() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    expense = _expense(
        "Mortgage",
        150_000,
        "biweekly",
        0,
        recurrence_anchor=date(2026, 8, 13),
    )
    occurrences = occurrences_in_cycle([expense], cycle)
    assert len(occurrences) == 1
    assert occurrences[0].due_date == date(2026, 8, 13)


def test_biweekly_occurrence_exactly_on_next_pay_date_belongs_to_next_cycle_only() -> None:
    # Because the biweekly period (14 days) equals the cycle length, an occurrence
    # exactly on this cycle's next_pay_date is also, by construction, 14 days after
    # this cycle's start_date - so it must land in the *next* cycle only, and this
    # cycle must instead pick up the occurrence at its own start_date. Confirms
    # FR-013: never assign a single occurrence to more than one cycle.
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    next_cycle = Cycle(
        start_date=date(2026, 8, 14),
        end_date=date(2026, 8, 27),
        next_pay_date=date(2026, 8, 28),
    )
    expense = _expense(
        "Mortgage",
        150_000,
        "biweekly",
        0,
        recurrence_anchor=date(2026, 8, 14),
    )
    this_cycle_occurrences = occurrences_in_cycle([expense], cycle)
    next_cycle_occurrences = occurrences_in_cycle([expense], next_cycle)
    assert [o.due_date for o in this_cycle_occurrences] == [date(2026, 7, 31)]
    assert [o.due_date for o in next_cycle_occurrences] == [date(2026, 8, 14)]


def test_biweekly_yields_exactly_one_occurrence_regardless_of_offset_from_pay_cycle() -> None:
    # Mortgage anchored on a Wednesday, independent of the Friday paycheck anchor -
    # every 14-day cycle must contain exactly one occurrence, never zero or two.
    mortgage_anchor = date(2026, 7, 1)  # a Wednesday, unrelated to the pay anchor
    expense = _expense(
        "Mortgage", 150_000, "biweekly", 0, recurrence_anchor=mortgage_anchor
    )
    pay_anchor = date(2026, 7, 31)
    for n in range(-5, 5):
        start = pay_anchor + timedelta(days=14 * n)
        cycle = Cycle(
            start_date=start,
            end_date=start + timedelta(days=13),
            next_pay_date=start + timedelta(days=14),
        )
        occurrences = occurrences_in_cycle([expense], cycle)
        assert len(occurrences) == 1
        assert cycle.start_date <= occurrences[0].due_date <= cycle.end_date


def test_biweekly_without_anchor_date_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        RecurringExpense(
            id=1,
            name="Mortgage",
            amount=150_000,
            recurrence_type="biweekly",
            recurrence_value=0,
            recurrence_anchor=None,
        )
