from __future__ import annotations

import math
from dataclasses import dataclass

CENTER = 100.0
RADIUS = 90.0

PALETTE: tuple[str, ...] = (
    "#2563eb",
    "#f97316",
    "#16a34a",
    "#dc2626",
    "#9333ea",
    "#0891b2",
    "#ca8a04",
    "#db2777",
)
LEFTOVER_COLOR = "#10b981"
LEFTOVER_LABEL = "Leftover"


@dataclass(frozen=True)
class ChartSlice:
    label: str
    amount: int
    percent: float
    color: str
    path_d: str | None
    is_full_circle: bool


@dataclass(frozen=True)
class CycleChart:
    slices: list[ChartSlice]
    overspent: bool
    overspent_amount: int


def _point_on_circle(degrees: float) -> tuple[float, float]:
    radians = math.radians(degrees)
    x = CENTER + RADIUS * math.sin(radians)
    y = CENTER - RADIUS * math.cos(radians)
    return x, y


def _arc_path(start_degrees: float, end_degrees: float) -> str:
    start_x, start_y = _point_on_circle(start_degrees)
    end_x, end_y = _point_on_circle(end_degrees)
    large_arc_flag = 1 if (end_degrees - start_degrees) > 180 else 0
    return (
        f"M {CENTER:.3f},{CENTER:.3f} "
        f"L {start_x:.3f},{start_y:.3f} "
        f"A {RADIUS:.3f},{RADIUS:.3f} 0 {large_arc_flag} 1 {end_x:.3f},{end_y:.3f} Z"
    )


def build_chart(
    pay_amount: int, totals: list[tuple[str, int]], leftover_amount: int
) -> CycleChart:
    total_expenses = sum(amount for _, amount in totals)
    overspent = leftover_amount < 0
    overspent_amount = -leftover_amount if overspent else 0
    denominator = total_expenses if overspent else pay_amount

    entries: list[tuple[str, int]] = sorted(
        ((label, amount) for label, amount in totals if amount > 0),
        key=lambda item: item[0],
    )
    if not overspent and leftover_amount > 0:
        entries.append((LEFTOVER_LABEL, leftover_amount))

    if not entries:
        return CycleChart(slices=[], overspent=overspent, overspent_amount=overspent_amount)

    category_labels = [label for label, _ in entries if label != LEFTOVER_LABEL]
    colors = {label: PALETTE[i % len(PALETTE)] for i, label in enumerate(category_labels)}
    colors[LEFTOVER_LABEL] = LEFTOVER_COLOR

    if len(entries) == 1:
        label, amount = entries[0]
        slices = [
            ChartSlice(
                label=label,
                amount=amount,
                percent=100.0,
                color=colors[label],
                path_d=None,
                is_full_circle=True,
            )
        ]
        return CycleChart(slices=slices, overspent=overspent, overspent_amount=overspent_amount)

    slices = []
    cumulative_degrees = 0.0
    for label, amount in entries:
        percent = amount / denominator * 100
        sweep_degrees = percent / 100 * 360
        slices.append(
            ChartSlice(
                label=label,
                amount=amount,
                percent=percent,
                color=colors[label],
                path_d=_arc_path(cumulative_degrees, cumulative_degrees + sweep_degrees),
                is_full_circle=False,
            )
        )
        cumulative_degrees += sweep_degrees

    return CycleChart(slices=slices, overspent=overspent, overspent_amount=overspent_amount)
