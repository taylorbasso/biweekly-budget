from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from budget.models import PaySchedule

CYCLE_LENGTH_DAYS = 14


@dataclass(frozen=True)
class Cycle:
    start_date: date
    end_date: date
    next_pay_date: date


def resolve_cycle(pay_schedule: PaySchedule, reference_date: date) -> Cycle:
    days_since_anchor = (reference_date - pay_schedule.anchor_date).days
    cycles_elapsed = days_since_anchor // CYCLE_LENGTH_DAYS
    start_date = pay_schedule.anchor_date + timedelta(
        days=CYCLE_LENGTH_DAYS * cycles_elapsed
    )
    next_pay_date = start_date + timedelta(days=CYCLE_LENGTH_DAYS)
    end_date = next_pay_date - timedelta(days=1)
    return Cycle(start_date=start_date, end_date=end_date, next_pay_date=next_pay_date)
