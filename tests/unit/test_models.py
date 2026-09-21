from __future__ import annotations

import pytest

from budget.models import Account, CreditAccount, RecurringExpense, ValidationError


def test_recurring_expense_defaults_essential_false() -> None:
    expense = RecurringExpense(
        id=1,
        name="Rent",
        amount=1000,
        recurrence_type="day_of_month",
        recurrence_value=1,
    )
    assert expense.essential is False


def test_recurring_expense_can_be_marked_essential() -> None:
    expense = RecurringExpense(
        id=1,
        name="Rent",
        amount=1000,
        recurrence_type="day_of_month",
        recurrence_value=1,
        essential=True,
    )
    assert expense.essential is True


def test_account_defaults_zero_percent() -> None:
    account = Account(id=None, name="Cash", balance=500)
    assert account.penalty_tax_percent == 0


def test_account_rejects_negative_balance() -> None:
    with pytest.raises(ValidationError):
        Account(id=None, name="Cash", balance=-1)


def test_account_rejects_percent_below_zero() -> None:
    with pytest.raises(ValidationError):
        Account(id=None, name="401k", balance=100, penalty_tax_percent=-1)


def test_account_rejects_percent_above_100() -> None:
    with pytest.raises(ValidationError):
        Account(id=None, name="401k", balance=100, penalty_tax_percent=101)


def test_account_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        Account(id=None, name="   ", balance=100)


def test_credit_account_defaults() -> None:
    account = CreditAccount(id=None, name="Visa", balance=200_000)
    assert account.interest_rate == 0
    assert account.minimum_payment == 0
    assert account.actual_payment == 0


def test_credit_account_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        CreditAccount(id=None, name="   ", balance=100)


def test_credit_account_rejects_negative_balance() -> None:
    with pytest.raises(ValidationError):
        CreditAccount(id=None, name="Visa", balance=-1)


def test_credit_account_rejects_negative_interest_rate() -> None:
    with pytest.raises(ValidationError):
        CreditAccount(id=None, name="Visa", balance=100, interest_rate=-1)


def test_credit_account_rejects_negative_minimum_payment() -> None:
    with pytest.raises(ValidationError):
        CreditAccount(id=None, name="Visa", balance=100, minimum_payment=-1)


def test_credit_account_rejects_negative_actual_payment() -> None:
    with pytest.raises(ValidationError):
        CreditAccount(id=None, name="Visa", balance=100, actual_payment=-1)
