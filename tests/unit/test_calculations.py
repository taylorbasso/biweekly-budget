from __future__ import annotations

from datetime import date, timedelta
from fractions import Fraction

import pytest

from budget.calculations import (
    UNCATEGORIZED,
    account_spendable,
    annual_cost,
    compute_annual_cost_breakdown,
    compute_breakdown,
    compute_debts,
    compute_leftover,
    compute_runway,
    effective_payment,
    essential_monthly_burn,
    group_debts,
    group_expenses_by_category,
    monthly_equivalent,
    occurrences_in_cycle,
    payoff_month,
    payoff_months,
    total_spendable,
    utilization_percent,
)
from budget.cycles import Cycle
from budget.models import (
    Account,
    Debt,
    PaySchedule,
    RecurringExpense,
    ValidationError,
)


def _expense(
    name: str,
    amount: int,
    recurrence_type: str,
    recurrence_value: int,
    category: str | None = None,
    expense_id: int | None = 1,
    recurrence_anchor: date | None = None,
    essential: bool = False,
) -> RecurringExpense:
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
    result = compute_leftover(schedule, occurrences, cycle, cycle.start_date)
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
    result = compute_leftover(schedule, occurrences, cycle, cycle.start_date)
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
    result = compute_leftover(schedule, occurrences, cycle, cycle.start_date)
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

    leftover = compute_leftover(schedule, occurrences, cycle, cycle.start_date)
    assert sum(amount for _, amount in breakdown.totals) == leftover.total_expenses


def test_breakdown_items_group_by_name_within_category_summing_duplicates() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    expenses = [
        _expense("Rent", 120_000, "day_of_month", 1, category="Housing", expense_id=1),
        _expense(
            "Investment",
            10_000,
            "day_of_week",
            4,
            category="Investments",
            expense_id=2,
        ),  # occurs twice in this 14-day cycle
    ]
    occurrences = occurrences_in_cycle(expenses, cycle)
    breakdown = compute_breakdown(cycle, occurrences)
    assert breakdown.items["Housing"] == [("Rent", 120_000)]
    # Two Friday occurrences of the same expense are summed into a single named entry.
    assert breakdown.items["Investments"] == [("Investment", 20_000)]


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


def test_annual_cost_day_of_month_expense_multiplies_by_twelve() -> None:
    expense = _expense("Rent", 120_000, "day_of_month", 1, category="Housing")
    assert annual_cost(expense) == 120_000 * 12


def test_annual_cost_day_of_week_expense_multiplies_by_fifty_two() -> None:
    expense = _expense(
        "Investment transfer", 10_000, "day_of_week", 4, category="Investments"
    )
    assert annual_cost(expense) == 10_000 * 52


def test_annual_cost_biweekly_expense_multiplies_by_twenty_six() -> None:
    expense = _expense(
        "Mortgage", 150_000, "biweekly", 0, recurrence_anchor=date(2026, 7, 31)
    )
    assert annual_cost(expense) == 150_000 * 26


def test_annual_cost_breakdown_grand_total_sums_every_item() -> None:
    expenses = [
        _expense("Rent", 120_000, "day_of_month", 1, category="Housing", expense_id=1),
        _expense(
            "Investment transfer",
            10_000,
            "day_of_week",
            4,
            category="Investments",
            expense_id=2,
        ),
        _expense("Streaming", 1_500, "day_of_month", 31, expense_id=3),
    ]
    breakdown = compute_annual_cost_breakdown(expenses)
    assert breakdown.grand_total == 120_000 * 12 + 10_000 * 52 + 1_500 * 12


def test_annual_cost_breakdown_empty_expense_list_yields_zero_total() -> None:
    breakdown = compute_annual_cost_breakdown([])
    assert breakdown.categories == []
    assert breakdown.grand_total == 0


def test_annual_cost_breakdown_orders_categories_by_subtotal_descending() -> None:
    expenses = [
        _expense("Coffee", 500, "day_of_week", 1, category="Antiques", expense_id=1),
        _expense("Rent", 120_000, "day_of_month", 1, category="Zoning", expense_id=2),
        _expense("Streaming", 1_500, "day_of_month", 31, expense_id=3),
    ]
    breakdown = compute_annual_cost_breakdown(expenses)
    # Zoning 1,440,000 > Antiques 26,000 > Uncategorized 18,000 (not alphabetical)
    assert [category.category for category in breakdown.categories] == [
        "Zoning",
        "Antiques",
        UNCATEGORIZED,
    ]


def test_annual_cost_breakdown_equal_subtotals_order_by_category_name() -> None:
    expenses = [
        _expense("B", 1_000, "day_of_month", 1, category="Beta", expense_id=1),
        _expense("A", 1_000, "day_of_month", 1, category="Alpha", expense_id=2),
    ]
    breakdown = compute_annual_cost_breakdown(expenses)
    assert [category.category for category in breakdown.categories] == ["Alpha", "Beta"]


def test_annual_cost_breakdown_monthly_total_is_grand_total_over_twelve() -> None:
    # $79.99 monthly + $150 weekly = 95,988 + 780,000 = 875,988 cents/yr -> 72,999 /mo
    expenses = [
        _expense("Internet", 7_999, "day_of_month", 22, category="Utilities", expense_id=1),
        _expense("Groceries", 15_000, "day_of_week", 5, category="Food", expense_id=2),
    ]
    breakdown = compute_annual_cost_breakdown(expenses)
    assert breakdown.monthly_total == 72_999


def test_annual_cost_breakdown_empty_list_has_zero_monthly_total() -> None:
    assert compute_annual_cost_breakdown([]).monthly_total == 0


def test_annual_cost_breakdown_sorts_within_category_by_annual_cost_descending() -> None:
    expenses = [
        _expense("Rent", 120_000, "day_of_month", 1, category="Housing", expense_id=1),
        _expense(
            "Renters insurance", 1_000, "day_of_month", 5, category="Housing", expense_id=2
        ),
    ]
    breakdown = compute_annual_cost_breakdown(expenses)
    housing = next(c for c in breakdown.categories if c.category == "Housing")
    assert [item.name for item in housing.items] == ["Rent", "Renters insurance"]


def test_annual_cost_breakdown_ties_break_by_name_ascending() -> None:
    expenses = [
        _expense("Zeta", 10_00, "day_of_month", 1, category="Housing", expense_id=1),
        _expense("Alpha", 10_00, "day_of_month", 2, category="Housing", expense_id=2),
    ]
    breakdown = compute_annual_cost_breakdown(expenses)
    housing = next(c for c in breakdown.categories if c.category == "Housing")
    assert [item.name for item in housing.items] == ["Alpha", "Zeta"]


def test_annual_cost_breakdown_category_subtotal_sums_its_items() -> None:
    expenses = [
        _expense("Rent", 120_000, "day_of_month", 1, category="Housing", expense_id=1),
        _expense(
            "Renters insurance", 1_000, "day_of_month", 5, category="Housing", expense_id=2
        ),
    ]
    breakdown = compute_annual_cost_breakdown(expenses)
    housing = next(c for c in breakdown.categories if c.category == "Housing")
    assert housing.subtotal == 120_000 * 12 + 1_000 * 12


def test_remaining_expenses_excludes_only_strictly_past_due_occurrences() -> None:
    cycle = Cycle(
        start_date=date(2026, 7, 31),
        end_date=date(2026, 8, 13),
        next_pay_date=date(2026, 8, 14),
    )
    schedule = PaySchedule(anchor_date=date(2026, 7, 31), amount=200_000)
    expenses = [
        _expense("Past due", 10_000, "day_of_month", 31, expense_id=1),  # July 31
        _expense("Due today", 20_000, "day_of_month", 5, expense_id=2),  # Aug 5
        _expense("Upcoming", 30_000, "day_of_month", 13, expense_id=3),  # Aug 13
    ]
    occurrences = occurrences_in_cycle(expenses, cycle)
    reference_date = date(2026, 8, 5)
    result = compute_leftover(schedule, occurrences, cycle, reference_date)
    assert result.total_expenses == 60_000
    # "Due today" and "Upcoming" remain; "Past due" (July 31) is excluded.
    assert result.remaining_expenses == 50_000
    assert [o.name for o in result.upcoming] == ["Due today", "Upcoming"]
    assert [o.name for o in result.earlier] == ["Past due"]


def test_monthly_equivalent_day_of_month_equals_amount() -> None:
    expense = _expense("Rent", 200_000, "day_of_month", 1)
    assert monthly_equivalent(expense) == Fraction(200_000)


def test_monthly_equivalent_day_of_week_is_exact_fraction() -> None:
    expense = _expense("Investment", 10_000, "day_of_week", 4)
    assert monthly_equivalent(expense) == Fraction(10_000 * 52, 12)


def test_monthly_equivalent_biweekly_is_exact_fraction() -> None:
    expense = _expense(
        "Storage", 150_000, "biweekly", 0, recurrence_anchor=date(2026, 1, 1)
    )
    assert monthly_equivalent(expense) == Fraction(150_000 * 26, 12)


def test_essential_monthly_burn_sums_only_essential_expenses() -> None:
    expenses = [
        _expense("Rent", 200_000, "day_of_month", 1, expense_id=1, essential=True),
        _expense("Streaming", 1_500, "day_of_month", 31, expense_id=2, essential=False),
    ]
    assert essential_monthly_burn(expenses) == Fraction(200_000)


def test_essential_monthly_burn_is_zero_when_none_essential() -> None:
    expenses = [_expense("Streaming", 1_500, "day_of_month", 31, essential=False)]
    assert essential_monthly_burn(expenses) == Fraction(0)


def test_account_spendable_full_balance_at_zero_percent() -> None:
    account = Account(id=None, name="Cash", balance=200_000, penalty_tax_percent=0)
    assert account_spendable(account) == Fraction(200_000)


def test_account_spendable_applies_haircut() -> None:
    account = Account(id=None, name="401k", balance=1_000_000, penalty_tax_percent=30)
    assert account_spendable(account) == Fraction(700_000)


def test_total_spendable_sums_multiple_accounts() -> None:
    accounts = [
        Account(id=1, name="Cash", balance=200_000, penalty_tax_percent=0),
        Account(id=2, name="401k", balance=1_000_000, penalty_tax_percent=30),
    ]
    assert total_spendable(accounts) == Fraction(900_000)


def test_total_spendable_is_zero_with_no_accounts() -> None:
    assert total_spendable([]) == Fraction(0)


def test_compute_runway_single_account_matches_spec_example() -> None:
    expenses = [_expense("Rent", 200_000, "day_of_month", 1, essential=True)]
    accounts = [Account(id=1, name="Cash", balance=706_000, penalty_tax_percent=0)]
    result = compute_runway(expenses, accounts)
    assert result.months == pytest.approx(3.53)


def test_compute_runway_multiple_accounts_matches_spec_example() -> None:
    expenses = [_expense("Rent", 200_000, "day_of_month", 1, essential=True)]
    accounts = [
        Account(id=1, name="Cash", balance=200_000, penalty_tax_percent=0),
        Account(id=2, name="401k", balance=1_000_000, penalty_tax_percent=30),
    ]
    result = compute_runway(expenses, accounts)
    assert result.months == pytest.approx(4.5)


def test_compute_runway_months_none_when_no_essential_expenses() -> None:
    expenses = [_expense("Streaming", 1_500, "day_of_month", 31, essential=False)]
    accounts = [Account(id=1, name="Cash", balance=706_000, penalty_tax_percent=0)]
    result = compute_runway(expenses, accounts)
    assert result.months is None


def test_compute_runway_months_zero_when_no_accounts() -> None:
    expenses = [_expense("Rent", 200_000, "day_of_month", 1, essential=True)]
    result = compute_runway(expenses, [])
    assert result.months == 0.0


def test_payoff_months_zero_balance_is_already_paid_off() -> None:
    assert payoff_months(0, 20.0, 10_000) == 0


def test_payoff_months_zero_payment_never_pays_off() -> None:
    assert payoff_months(200_000, 20.0, 0) is None


def test_payoff_months_payment_below_monthly_interest_never_pays_off() -> None:
    # $1,000 balance at 24% APR accrues $20/month interest; a $10/month payment
    # never exceeds that, so the balance never shrinks.
    assert payoff_months(100_000, 24.0, 1_000) is None


def test_payoff_months_zero_interest_rate_is_simple_division() -> None:
    assert payoff_months(100_000, 0.0, 30_000) == 4  # ceil(100000/30000) == 4


def test_payoff_months_matches_quickstart_visa_example() -> None:
    # $2,000 balance, 20% APR, $100/month -> ~24.5 months, rounds up to 25
    assert payoff_months(200_000, 20.0, 10_000) == 25


def test_payoff_months_matches_quickstart_car_loan_example() -> None:
    # $5,000 balance, 6% APR, $150/month -> ~36.6 months, rounds up to 37
    assert payoff_months(500_000, 6.0, 15_000) == 37


TODAY = date(2026, 10, 20)


def test_payoff_month_counts_forward_from_this_month() -> None:
    assert payoff_month(date(2026, 10, 20), 17) == date(2028, 3, 1)


def test_payoff_month_rolls_over_december() -> None:
    assert payoff_month(date(2026, 12, 31), 1) == date(2027, 1, 1)


def test_payoff_month_zero_months_is_this_month() -> None:
    assert payoff_month(date(2026, 2, 28), 0) == date(2026, 2, 1)


def test_payoff_month_never_pays_off_is_none() -> None:
    assert payoff_month(date(2026, 10, 20), None) is None


def test_effective_payment_uses_actual_when_positive() -> None:
    account = Debt(
        id=1,
        name="Visa",
        balance=200_000,
        interest_rate=20.0,
        minimum_payment=5_000,
        actual_payment=10_000,
    )
    assert effective_payment(account) == 10_000


def test_effective_payment_falls_back_to_minimum_when_actual_unset() -> None:
    account = Debt(
        id=1,
        name="Car Loan",
        balance=500_000,
        interest_rate=6.0,
        minimum_payment=15_000,
        actual_payment=0,
    )
    assert effective_payment(account) == 15_000


def test_compute_debts_sums_columns_independently() -> None:
    accounts = [
        Debt(
            id=1,
            name="Visa",
            balance=200_000,
            interest_rate=20.0,
            minimum_payment=5_000,
            actual_payment=10_000,
        ),
        Debt(
            id=2,
            name="Car Loan",
            balance=500_000,
            interest_rate=6.0,
            minimum_payment=15_000,
            actual_payment=0,
        ),
    ]
    rows, totals = compute_debts(accounts, TODAY)
    assert [row.debt.name for row in rows] == ["Visa", "Car Loan"]
    assert totals.balance == 700_000
    assert totals.minimum_payment == 20_000
    # What is actually paid each month: Visa's $100 actual + Car Loan's $150
    # minimum (no actual payment set, so it falls back to the minimum).
    assert totals.monthly_payment == 25_000
    assert [row.monthly_payment for row in rows] == [10_000, 15_000]


def test_compute_debts_empty_list_gives_zero_totals() -> None:
    rows, totals = compute_debts([], TODAY)
    assert rows == []
    assert totals.balance == 0
    assert totals.minimum_payment == 0
    assert totals.monthly_payment == 0
    assert totals.credit_limit == 0
    assert totals.utilization_percent is None
    assert totals.debt_free_month is None


def test_utilization_percent_normal_case() -> None:
    assert utilization_percent(30_000, 100_000) == pytest.approx(30.0)


def test_utilization_percent_zero_limit_is_not_applicable() -> None:
    assert utilization_percent(30_000, 0) is None


def test_utilization_percent_can_exceed_100_when_over_limit() -> None:
    assert utilization_percent(120_000, 100_000) == pytest.approx(120.0)


def test_compute_debts_includes_per_row_and_total_utilization() -> None:
    accounts = [
        Debt(id=1, name="Visa", balance=30_000, credit_limit=100_000),
        Debt(id=2, name="No Limit Tracked", balance=50_000, credit_limit=0),
    ]
    rows, totals = compute_debts(accounts, TODAY)
    assert rows[0].utilization_percent == pytest.approx(30.0)
    assert rows[1].utilization_percent is None
    assert totals.credit_limit == 100_000
    # Aggregate usage counts only balances that have a credit limit (loans
    # don't), and is computed once rather than averaged: 30,000 / 100,000.
    assert totals.utilization_percent == pytest.approx(30.0)


def test_compute_debts_total_utilization_ignores_loan_balances() -> None:
    accounts = [
        Debt(id=1, name="Card A", balance=345_012, credit_limit=1_500_000),
        Debt(id=2, name="Student loan", balance=1_823_400, credit_limit=0),
        Debt(id=3, name="Card B", balance=50_000, credit_limit=500_000),
    ]
    _, totals = compute_debts(accounts, TODAY)
    assert totals.balance == 345_012 + 1_823_400 + 50_000
    assert totals.utilization_percent == pytest.approx(395_012 / 2_000_000 * 100)


def test_compute_debts_rows_carry_payoff_month() -> None:
    accounts = [
        Debt(
            id=1, name="Visa", balance=200_000, interest_rate=20.0, actual_payment=10_000
        ),
        Debt(id=2, name="Stuck", balance=100_000, interest_rate=24.0),
    ]
    rows, _ = compute_debts(accounts, TODAY)
    assert rows[0].payoff_months == 25
    assert rows[0].payoff_month == date(2028, 11, 1)
    assert rows[1].payoff_month is None


def test_compute_debts_debt_free_month_is_latest_payoff() -> None:
    accounts = [
        Debt(
            id=1, name="Visa", balance=200_000, interest_rate=20.0, actual_payment=10_000
        ),
        Debt(
            id=2, name="Car", balance=500_000, interest_rate=6.0, minimum_payment=15_000
        ),
    ]
    _, totals = compute_debts(accounts, TODAY)
    # Visa: 25 months -> Nov 2028; Car: 37 months -> Nov 2029
    assert totals.debt_free_month == date(2029, 11, 1)


def test_compute_debts_no_debt_free_month_if_any_balance_never_pays_off() -> None:
    accounts = [
        Debt(
            id=1, name="Visa", balance=200_000, interest_rate=20.0, actual_payment=10_000
        ),
        Debt(id=2, name="Stuck", balance=100_000, interest_rate=24.0),
    ]
    _, totals = compute_debts(accounts, TODAY)
    assert totals.debt_free_month is None


def test_compute_debts_no_debt_free_month_when_nothing_is_owed() -> None:
    accounts = [Debt(id=1, name="Paid card", balance=0, credit_limit=100_000)]
    _, totals = compute_debts(accounts, TODAY)
    assert totals.debt_free_month is None


def test_group_expenses_by_category_orders_categories_case_insensitively_uncategorized_last() -> None:
    expenses = [
        _expense("Streaming", 1_500, "day_of_month", 20, expense_id=1),
        _expense("Rent", 145_000, "day_of_month", 1, category="housing", expense_id=2),
        _expense("Groceries", 15_000, "day_of_week", 5, category="Food", expense_id=3),
        _expense("Zoo pass", 2_000, "day_of_month", 3, category="Zoo", expense_id=4),
    ]
    groups = group_expenses_by_category(expenses)
    assert [group.category for group in groups] == ["Food", "housing", "Zoo", UNCATEGORIZED]


def test_group_expenses_by_category_mixes_recurrence_types_in_one_group() -> None:
    expenses = [
        _expense("Takeout", 4_000, "day_of_week", 4, category="Food", expense_id=1),
        _expense("Groceries", 50_000, "day_of_month", 1, category="Food", expense_id=2),
    ]
    groups = group_expenses_by_category(expenses)
    assert len(groups) == 1
    assert [expense.name for expense in groups[0].expenses] == ["Groceries", "Takeout"]


def test_group_expenses_by_category_sorts_names_case_insensitively() -> None:
    expenses = [
        _expense("water", 3_000, "day_of_month", 5, category="Utilities", expense_id=1),
        _expense("Electric", 9_500, "day_of_month", 15, category="Utilities", expense_id=2),
    ]
    groups = group_expenses_by_category(expenses)
    assert [expense.name for expense in groups[0].expenses] == ["Electric", "water"]


def test_group_expenses_by_category_monthly_total_uses_monthly_equivalents() -> None:
    # $150 weekly = 150 * 52 / 12 = $650.00; $380 biweekly = 380 * 26 / 12 = $823.33...
    expenses = [
        _expense("Groceries", 15_000, "day_of_week", 5, category="Mixed", expense_id=1),
        _expense(
            "Car payment",
            38_000,
            "biweekly",
            0,
            category="Mixed",
            expense_id=2,
            recurrence_anchor=date(2026, 10, 10),
        ),
        _expense("Rent", 145_000, "day_of_month", 1, category="Mixed", expense_id=3),
    ]
    groups = group_expenses_by_category(expenses)
    # 65_000 + 82_333.33... + 145_000 = 292_333.33... cents, rounded once
    assert groups[0].monthly_total == 292_333


def test_group_expenses_by_category_rounds_the_sum_not_each_item() -> None:
    # Two $1.00 biweekly items: each is 216.67 cents/month; rounding each would give 434.
    expenses = [
        _expense(
            "A",
            100,
            "biweekly",
            0,
            category="Fees",
            expense_id=1,
            recurrence_anchor=date(2026, 1, 2),
        ),
        _expense(
            "B",
            100,
            "biweekly",
            0,
            category="Fees",
            expense_id=2,
            recurrence_anchor=date(2026, 1, 2),
        ),
    ]
    assert group_expenses_by_category(expenses)[0].monthly_total == 433


def test_group_expenses_by_category_empty_list_yields_no_groups() -> None:
    assert group_expenses_by_category([]) == []


def test_group_debts_puts_credit_cards_before_loans() -> None:
    debts = [
        Debt(id=1, name="Car", balance=500_000, interest_rate=6.0, kind="loan"),
        Debt(id=2, name="Visa", balance=100_000, interest_rate=20.0, credit_limit=500_000),
    ]
    rows, _ = compute_debts(debts, TODAY)
    groups = group_debts(rows)
    assert [group.kind for group in groups] == ["credit_card", "loan"]
    assert [row.debt.name for row in groups[0].rows] == ["Visa"]
    assert [row.debt.name for row in groups[1].rows] == ["Car"]


def test_group_debts_omits_empty_groups() -> None:
    rows, _ = compute_debts([Debt(id=1, name="Car", balance=1, kind="loan")], TODAY)
    assert [group.kind for group in group_debts(rows)] == ["loan"]


def test_group_debts_orders_highest_interest_first_then_name() -> None:
    debts = [
        Debt(id=1, name="Low", balance=1_000, interest_rate=5.0),
        Debt(id=2, name="Zed", balance=1_000, interest_rate=24.99),
        Debt(id=3, name="Abe", balance=1_000, interest_rate=24.99),
    ]
    rows, _ = compute_debts(debts, TODAY)
    assert [row.debt.name for row in group_debts(rows)[0].rows] == ["Abe", "Zed", "Low"]


def test_group_debts_subtotals_and_card_usage() -> None:
    debts = [
        Debt(id=1, name="A", balance=345_012, credit_limit=1_500_000, actual_payment=25_000),
        Debt(id=2, name="B", balance=50_000, credit_limit=500_000, minimum_payment=2_500),
        Debt(id=3, name="Loan", balance=1_823_400, minimum_payment=21_000, kind="loan"),
    ]
    rows, _ = compute_debts(debts, TODAY)
    cards, loans = group_debts(rows)
    assert cards.balance == 395_012
    assert cards.monthly_payment == 27_500
    assert cards.credit_limit == 2_000_000
    assert cards.utilization_percent == pytest.approx(395_012 / 2_000_000 * 100)
    assert loans.balance == 1_823_400
    assert loans.monthly_payment == 21_000
    assert loans.utilization_percent is None


def test_group_debts_card_usage_ignores_cards_without_a_limit() -> None:
    debts = [
        Debt(id=1, name="Tracked", balance=30_000, credit_limit=100_000),
        Debt(id=2, name="No limit entered", balance=50_000),
    ]
    rows, _ = compute_debts(debts, TODAY)
    (cards,) = group_debts(rows)
    assert cards.balance == 80_000
    assert cards.utilization_percent == pytest.approx(30.0)
