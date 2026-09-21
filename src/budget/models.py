from __future__ import annotations

from dataclasses import dataclass
from datetime import date

RECURRENCE_TYPES = ("day_of_month", "day_of_week", "biweekly")


class ValidationError(ValueError):
    """Raised when a PaySchedule or RecurringExpense fails validation."""


@dataclass(frozen=True)
class PaySchedule:
    anchor_date: date
    amount: int  # integer cents

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValidationError("amount must be greater than 0")


@dataclass(frozen=True)
class RecurringExpense:
    id: int | None
    name: str
    amount: int  # integer cents
    recurrence_type: str
    recurrence_value: int
    category: str | None = None
    recurrence_anchor: date | None = None  # required when recurrence_type == "biweekly"
    essential: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("name must not be empty")
        if self.amount <= 0:
            raise ValidationError("amount must be greater than 0")
        if self.recurrence_type not in RECURRENCE_TYPES:
            raise ValidationError(
                f"recurrence_type must be one of {RECURRENCE_TYPES}"
            )
        if self.recurrence_type == "day_of_month" and not (
            1 <= self.recurrence_value <= 31
        ):
            raise ValidationError("day_of_month recurrence_value must be in 1..31")
        if self.recurrence_type == "day_of_week" and not (
            0 <= self.recurrence_value <= 6
        ):
            raise ValidationError("day_of_week recurrence_value must be in 0..6")
        if self.recurrence_type == "biweekly" and self.recurrence_anchor is None:
            raise ValidationError("biweekly recurrence requires an anchor date")


@dataclass(frozen=True)
class Account:
    id: int | None
    name: str
    balance: int  # integer cents
    penalty_tax_percent: int = 0  # 0..100, portion lost to early-withdrawal/tax

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("name must not be empty")
        if self.balance < 0:
            raise ValidationError("balance must not be negative")
        if not (0 <= self.penalty_tax_percent <= 100):
            raise ValidationError("penalty_tax_percent must be in 0..100")


@dataclass(frozen=True)
class CreditAccount:
    id: int | None
    name: str
    balance: int  # integer cents
    interest_rate: float = 0  # annual percentage, e.g. 24.99 means 24.99% APR
    minimum_payment: int = 0  # integer cents
    actual_payment: int = 0  # integer cents; 0 means "not set" (falls back to minimum)
    credit_limit: int = 0  # integer cents; 0 means "not tracked" (usage % shown as N/A)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("name must not be empty")
        if self.balance < 0:
            raise ValidationError("balance must not be negative")
        if self.interest_rate < 0:
            raise ValidationError("interest_rate must not be negative")
        if self.minimum_payment < 0:
            raise ValidationError("minimum_payment must not be negative")
        if self.actual_payment < 0:
            raise ValidationError("actual_payment must not be negative")
        if self.credit_limit < 0:
            raise ValidationError("credit_limit must not be negative")
