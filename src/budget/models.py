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
