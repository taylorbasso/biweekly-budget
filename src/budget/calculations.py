from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from budget.cycles import Cycle
from budget.models import PaySchedule, RecurringExpense

UNCATEGORIZED = "Uncategorized"


@dataclass(frozen=True)
class ExpenseOccurrence:
    expense_id: int | None
    name: str
    due_date: date
    amount: int
    category: str


@dataclass(frozen=True)
class LeftoverResult:
    cycle: Cycle
    pay_amount: int
    occurrences: list[ExpenseOccurrence]
    total_expenses: int
    leftover_amount: int


@dataclass(frozen=True)
class CategoryBreakdown:
    cycle: Cycle
    totals: list[tuple[str, int]]


def _months_spanning(start: date, end: date) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return months


def _day_of_month_occurrence(
    expense: RecurringExpense, cycle: Cycle
) -> ExpenseOccurrence | None:
    for year, month in _months_spanning(cycle.start_date, cycle.end_date):
        last_day = calendar.monthrange(year, month)[1]
        due_day = min(expense.recurrence_value, last_day)
        due_date = date(year, month, due_day)
        if cycle.start_date <= due_date <= cycle.end_date:
            return ExpenseOccurrence(
                expense_id=expense.id,
                name=expense.name,
                due_date=due_date,
                amount=expense.amount,
                category=expense.category or UNCATEGORIZED,
            )
    return None


def _day_of_week_occurrences(
    expense: RecurringExpense, cycle: Cycle
) -> list[ExpenseOccurrence]:
    occurrences: list[ExpenseOccurrence] = []
    current = cycle.start_date
    while current <= cycle.end_date:
        if current.weekday() == expense.recurrence_value:
            occurrences.append(
                ExpenseOccurrence(
                    expense_id=expense.id,
                    name=expense.name,
                    due_date=current,
                    amount=expense.amount,
                    category=expense.category or UNCATEGORIZED,
                )
            )
        current += timedelta(days=1)
    return occurrences


def _biweekly_occurrence(
    expense: RecurringExpense, cycle: Cycle
) -> ExpenseOccurrence | None:
    anchor = expense.recurrence_anchor
    assert anchor is not None
    current = cycle.start_date
    while current <= cycle.end_date:
        if (current - anchor).days % 14 == 0:
            return ExpenseOccurrence(
                expense_id=expense.id,
                name=expense.name,
                due_date=current,
                amount=expense.amount,
                category=expense.category or UNCATEGORIZED,
            )
        current += timedelta(days=1)
    return None


def occurrences_in_cycle(
    expenses: list[RecurringExpense], cycle: Cycle
) -> list[ExpenseOccurrence]:
    occurrences: list[ExpenseOccurrence] = []
    for expense in expenses:
        if expense.recurrence_type == "day_of_month":
            occurrence = _day_of_month_occurrence(expense, cycle)
            if occurrence is not None:
                occurrences.append(occurrence)
        elif expense.recurrence_type == "day_of_week":
            occurrences.extend(_day_of_week_occurrences(expense, cycle))
        else:
            occurrence = _biweekly_occurrence(expense, cycle)
            if occurrence is not None:
                occurrences.append(occurrence)
    return occurrences


def compute_leftover(
    pay_schedule: PaySchedule, occurrences: list[ExpenseOccurrence], cycle: Cycle
) -> LeftoverResult:
    total_expenses = sum(occurrence.amount for occurrence in occurrences)
    return LeftoverResult(
        cycle=cycle,
        pay_amount=pay_schedule.amount,
        occurrences=occurrences,
        total_expenses=total_expenses,
        leftover_amount=pay_schedule.amount - total_expenses,
    )


def compute_breakdown(
    cycle: Cycle, occurrences: list[ExpenseOccurrence]
) -> CategoryBreakdown:
    totals: dict[str, int] = {}
    for occurrence in occurrences:
        totals[occurrence.category] = totals.get(occurrence.category, 0) + occurrence.amount
    return CategoryBreakdown(cycle=cycle, totals=list(totals.items()))
