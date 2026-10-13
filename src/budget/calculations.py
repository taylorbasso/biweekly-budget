from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction

from budget.cycles import Cycle
from budget.models import Account, CreditAccount, PaySchedule, RecurringExpense

UNCATEGORIZED = "Uncategorized"

ANNUAL_COST_MULTIPLIERS: dict[str, int] = {
    "day_of_month": 12,
    "day_of_week": 52,
    "biweekly": 26,
}


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
    remaining_expenses: int


@dataclass(frozen=True)
class CategoryBreakdown:
    cycle: Cycle
    totals: list[tuple[str, int]]
    items: dict[str, list[tuple[str, int]]]


@dataclass(frozen=True)
class AnnualCostItem:
    expense_id: int | None
    name: str
    annual_cost: int
    percent_of_total: float


@dataclass(frozen=True)
class CategoryAnnualCost:
    category: str
    items: list[AnnualCostItem]
    subtotal: int
    percent_of_total: float


@dataclass(frozen=True)
class AnnualCostBreakdown:
    categories: list[CategoryAnnualCost]
    grand_total: int


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
    occurrences.sort(key=lambda occurrence: occurrence.due_date)
    return occurrences


def compute_leftover(
    pay_schedule: PaySchedule,
    occurrences: list[ExpenseOccurrence],
    cycle: Cycle,
    reference_date: date,
) -> LeftoverResult:
    total_expenses = sum(occurrence.amount for occurrence in occurrences)
    remaining_expenses = sum(
        occurrence.amount
        for occurrence in occurrences
        if occurrence.due_date >= reference_date
    )
    return LeftoverResult(
        cycle=cycle,
        pay_amount=pay_schedule.amount,
        occurrences=occurrences,
        total_expenses=total_expenses,
        leftover_amount=pay_schedule.amount - total_expenses,
        remaining_expenses=remaining_expenses,
    )


def compute_breakdown(
    cycle: Cycle, occurrences: list[ExpenseOccurrence]
) -> CategoryBreakdown:
    totals: dict[str, int] = {}
    items: dict[str, dict[str, int]] = {}
    for occurrence in occurrences:
        totals[occurrence.category] = totals.get(occurrence.category, 0) + occurrence.amount
        by_name = items.setdefault(occurrence.category, {})
        by_name[occurrence.name] = by_name.get(occurrence.name, 0) + occurrence.amount
    return CategoryBreakdown(
        cycle=cycle,
        totals=list(totals.items()),
        items={category: sorted(names.items()) for category, names in items.items()},
    )


def annual_cost(expense: RecurringExpense) -> int:
    return expense.amount * ANNUAL_COST_MULTIPLIERS[expense.recurrence_type]


@dataclass(frozen=True)
class RunwayResult:
    monthly_essential_burn: Fraction
    total_spendable: Fraction
    months: float | None


def monthly_equivalent(expense: RecurringExpense) -> Fraction:
    return Fraction(annual_cost(expense), 12)


def essential_monthly_burn(expenses: list[RecurringExpense]) -> Fraction:
    return sum(
        (monthly_equivalent(expense) for expense in expenses if expense.essential),
        Fraction(0),
    )


def account_spendable(account: Account) -> Fraction:
    return Fraction(account.balance * (100 - account.penalty_tax_percent), 100)


def total_spendable(accounts: list[Account]) -> Fraction:
    return sum((account_spendable(account) for account in accounts), Fraction(0))


def compute_runway(
    expenses: list[RecurringExpense], accounts: list[Account]
) -> RunwayResult:
    burn = essential_monthly_burn(expenses)
    spendable = total_spendable(accounts)
    months = float(spendable / burn) if burn > 0 else None
    return RunwayResult(
        monthly_essential_burn=burn, total_spendable=spendable, months=months
    )


def compute_annual_cost_breakdown(
    expenses: list[RecurringExpense],
) -> AnnualCostBreakdown:
    grand_total = sum(annual_cost(expense) for expense in expenses)

    def _percent(amount: int) -> float:
        return float(amount) / grand_total * 100 if grand_total else 0.0

    by_category: dict[str, list[AnnualCostItem]] = {}
    for expense in expenses:
        category = expense.category or UNCATEGORIZED
        cost = annual_cost(expense)
        by_category.setdefault(category, []).append(
            AnnualCostItem(
                expense_id=expense.id,
                name=expense.name,
                annual_cost=cost,
                percent_of_total=_percent(cost),
            )
        )

    categories = []
    for category in sorted(by_category):
        items = sorted(
            by_category[category], key=lambda item: (-item.annual_cost, item.name)
        )
        subtotal = sum(item.annual_cost for item in items)
        categories.append(
            CategoryAnnualCost(
                category=category,
                items=items,
                subtotal=subtotal,
                percent_of_total=_percent(subtotal),
            )
        )

    return AnnualCostBreakdown(categories=categories, grand_total=grand_total)


def payoff_months(balance: int, interest_rate: float, payment: int) -> int | None:
    if balance <= 0:
        return 0
    if payment <= 0:
        return None
    monthly_rate = interest_rate / 100 / 12
    if monthly_rate == 0:
        return math.ceil(balance / payment)
    monthly_interest = balance * monthly_rate
    if payment <= monthly_interest:
        return None
    n = -math.log(1 - monthly_rate * balance / payment) / math.log(1 + monthly_rate)
    return math.ceil(n)


def effective_payment(account: CreditAccount) -> int:
    return account.actual_payment if account.actual_payment > 0 else account.minimum_payment


def utilization_percent(balance: int, credit_limit: int) -> float | None:
    if credit_limit <= 0:
        return None
    return balance / credit_limit * 100


@dataclass(frozen=True)
class CreditAccountRow:
    account: CreditAccount
    payoff_months: int | None
    utilization_percent: float | None


@dataclass(frozen=True)
class CreditCardsTotals:
    balance: int
    minimum_payment: int
    actual_payment: int
    credit_limit: int
    utilization_percent: float | None


def compute_credit_cards(
    accounts: list[CreditAccount],
) -> tuple[list[CreditAccountRow], CreditCardsTotals]:
    rows = [
        CreditAccountRow(
            account=account,
            payoff_months=payoff_months(
                account.balance, account.interest_rate, effective_payment(account)
            ),
            utilization_percent=utilization_percent(account.balance, account.credit_limit),
        )
        for account in accounts
    ]
    total_balance = sum((account.balance for account in accounts), 0)
    total_credit_limit = sum((account.credit_limit for account in accounts), 0)
    totals = CreditCardsTotals(
        balance=total_balance,
        minimum_payment=sum((account.minimum_payment for account in accounts), 0),
        actual_payment=sum((account.actual_payment for account in accounts), 0),
        credit_limit=total_credit_limit,
        utilization_percent=utilization_percent(total_balance, total_credit_limit),
    )
    return rows, totals
