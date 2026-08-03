from __future__ import annotations

from budget.charts import PALETTE, build_chart


def test_categories_and_leftover_each_get_one_slice_summing_to_100_percent() -> None:
    chart = build_chart(
        pay_amount=200_000,
        totals=[("Housing", 120_000), ("Investments", 20_000), ("Uncategorized", 1_500)],
        leftover_amount=58_500,
    )
    assert not chart.overspent
    assert chart.overspent_amount == 0
    labels = [slice_.label for slice_ in chart.slices]
    assert labels == ["Housing", "Investments", "Uncategorized", "Leftover"]
    assert sum(slice_.percent for slice_ in chart.slices) == 100.0
    amounts = {slice_.label: slice_.amount for slice_ in chart.slices}
    assert amounts == {
        "Housing": 120_000,
        "Investments": 20_000,
        "Uncategorized": 1_500,
        "Leftover": 58_500,
    }


def test_zero_amount_category_is_omitted() -> None:
    chart = build_chart(
        pay_amount=100_000,
        totals=[("Housing", 100_000), ("Empty Category", 0)],
        leftover_amount=0,
    )
    labels = [slice_.label for slice_ in chart.slices]
    assert labels == ["Housing"]


def test_zero_expenses_yields_single_full_circle_leftover_slice() -> None:
    chart = build_chart(pay_amount=200_000, totals=[], leftover_amount=200_000)
    assert len(chart.slices) == 1
    slice_ = chart.slices[0]
    assert slice_.label == "Leftover"
    assert slice_.amount == 200_000
    assert slice_.percent == 100.0
    assert slice_.is_full_circle is True
    assert slice_.path_d is None


def test_single_remaining_category_after_zero_leftover_is_full_circle() -> None:
    chart = build_chart(
        pay_amount=100_000, totals=[("Housing", 100_000)], leftover_amount=0
    )
    assert len(chart.slices) == 1
    slice_ = chart.slices[0]
    assert slice_.label == "Housing"
    assert slice_.is_full_circle is True
    assert slice_.path_d is None


def test_multi_slice_charts_use_arc_paths_not_full_circle() -> None:
    chart = build_chart(
        pay_amount=100_000, totals=[("Housing", 50_000)], leftover_amount=50_000
    )
    assert len(chart.slices) == 2
    for slice_ in chart.slices:
        assert slice_.is_full_circle is False
        assert slice_.path_d is not None
        assert slice_.path_d.startswith("M ")


def test_colors_are_deterministic_and_categories_sorted_by_name() -> None:
    chart_a = build_chart(
        pay_amount=100_000,
        totals=[("Zebra", 10_000), ("Apple", 20_000)],
        leftover_amount=70_000,
    )
    chart_b = build_chart(
        pay_amount=100_000,
        totals=[("Apple", 20_000), ("Zebra", 10_000)],
        leftover_amount=70_000,
    )
    labels_a = [slice_.label for slice_ in chart_a.slices]
    labels_b = [slice_.label for slice_ in chart_b.slices]
    assert labels_a == ["Apple", "Zebra", "Leftover"]
    assert labels_a == labels_b

    colors_a = {slice_.label: slice_.color for slice_ in chart_a.slices}
    colors_b = {slice_.label: slice_.color for slice_ in chart_b.slices}
    assert colors_a == colors_b


def test_palette_wraps_after_eight_categories() -> None:
    totals = [(f"Category {i}", 1_000) for i in range(10)]
    chart = build_chart(pay_amount=100_000, totals=totals, leftover_amount=90_000)
    category_slices = [s for s in chart.slices if s.label != "Leftover"]
    assert len(category_slices) == 10
    assert category_slices[0].color == category_slices[len(PALETTE)].color


def test_leftover_color_is_reserved_and_not_in_category_palette() -> None:
    chart = build_chart(
        pay_amount=100_000, totals=[("Housing", 50_000)], leftover_amount=50_000
    )
    leftover_slice = next(s for s in chart.slices if s.label == "Leftover")
    assert leftover_slice.color not in PALETTE


def test_overspent_cycle_omits_leftover_slice_and_bases_percent_on_expenses() -> None:
    chart = build_chart(
        pay_amount=100_000,
        totals=[("Housing", 90_000), ("Subscriptions", 60_000)],
        leftover_amount=-50_000,
    )
    assert chart.overspent is True
    assert chart.overspent_amount == 50_000
    labels = [slice_.label for slice_ in chart.slices]
    assert "Leftover" not in labels
    assert sum(slice_.percent for slice_ in chart.slices) == 100.0
    percents = {slice_.label: slice_.percent for slice_ in chart.slices}
    assert percents["Housing"] == 60.0
    assert percents["Subscriptions"] == 40.0
