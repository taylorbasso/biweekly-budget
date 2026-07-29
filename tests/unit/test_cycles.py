from __future__ import annotations

from datetime import date

from budget.cycles import resolve_cycle
from budget.models import PaySchedule


def _schedule(anchor: str, amount: int = 200_000) -> PaySchedule:
    return PaySchedule(anchor_date=date.fromisoformat(anchor), amount=amount)


def test_reference_date_after_anchor_forward_projection() -> None:
    schedule = _schedule("2026-07-31")
    cycle = resolve_cycle(schedule, date(2026, 8, 1))
    assert cycle.start_date == date(2026, 7, 31)
    assert cycle.end_date == date(2026, 8, 13)
    assert cycle.next_pay_date == date(2026, 8, 14)


def test_reference_date_exactly_on_anchor() -> None:
    schedule = _schedule("2026-07-31")
    cycle = resolve_cycle(schedule, date(2026, 7, 31))
    assert cycle.start_date == date(2026, 7, 31)
    assert cycle.end_date == date(2026, 8, 13)
    assert cycle.next_pay_date == date(2026, 8, 14)


def test_reference_date_exactly_on_end_date() -> None:
    schedule = _schedule("2026-07-31")
    cycle = resolve_cycle(schedule, date(2026, 8, 13))
    assert cycle.start_date == date(2026, 7, 31)
    assert cycle.end_date == date(2026, 8, 13)


def test_reference_date_exactly_on_next_pay_date_belongs_to_next_cycle() -> None:
    schedule = _schedule("2026-07-31")
    cycle = resolve_cycle(schedule, date(2026, 8, 14))
    assert cycle.start_date == date(2026, 8, 14)
    assert cycle.end_date == date(2026, 8, 27)
    assert cycle.next_pay_date == date(2026, 8, 28)


def test_reference_date_before_anchor_backward_projection() -> None:
    schedule = _schedule("2026-07-31")
    cycle = resolve_cycle(schedule, date(2026, 7, 20))
    assert cycle.start_date == date(2026, 7, 17)
    assert cycle.end_date == date(2026, 7, 30)
    assert cycle.next_pay_date == date(2026, 7, 31)


def test_forward_projection_two_years_ahead_stays_aligned() -> None:
    schedule = _schedule("2026-01-01")
    cycle = resolve_cycle(schedule, date(2028, 1, 1))
    assert cycle.start_date <= date(2028, 1, 1) <= cycle.end_date
    assert (cycle.start_date - schedule.anchor_date).days % 14 == 0


def test_backward_projection_two_years_behind_stays_aligned() -> None:
    schedule = _schedule("2026-01-01")
    cycle = resolve_cycle(schedule, date(2024, 1, 1))
    assert cycle.start_date <= date(2024, 1, 1) <= cycle.end_date
    assert (cycle.start_date - schedule.anchor_date).days % 14 == 0
