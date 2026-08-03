# Research: Home Page Cycle Charts

No `NEEDS CLARIFICATION` markers remain in Technical Context. This document records the
design decisions made while filling it in.

## Decision 1: Chart rendering technology

**Decision**: Render the pie chart as an inline SVG string, built server-side in
`charts.py` and embedded directly in `leftover.html`.

**Rationale**: Constitution Principle I (Simplicity First) rules out adding frontend
build tooling, and the project has no JS dependency today. An inline SVG needs zero new
dependencies (stdlib `math` for trig), works with `TEMPLATES_AUTO_RELOAD`, and keeps all
chart logic testable as plain Python per Principle II.

**Alternatives considered**:
- *JS charting library (Chart.js, D3, etc.)*: rejected — adds a runtime dependency and,
  without a build step, would mean vendoring a script file or pulling from a CDN, which
  conflicts with Principle I (no frontend build tooling) and Principle IV (no network
  calls / no external resources loaded at runtime).
- *CSS `conic-gradient`*: viable for the wedge coloring but awkward for per-slice hover
  labels (FR-008) and legend text without extra markup anyway; SVG gives slices as real
  elements (`<path title>` / `<text>`) with no extra layer.

## Decision 2: Slice geometry algorithm

**Decision**: Compute each slice as an SVG `<path>` arc: convert each slice's share of
the total into a start/end angle (0° = 12 o'clock, clockwise), then compute arc
endpoints with `math.sin`/`math.cos` and emit a standard `M ... L ... A ... Z` path per
slice, plus a `<title>` child for hover text (FR-008).

**Rationale**: Standard, dependency-free technique for pie wedges in SVG; each slice is
an independent element so per-slice hover/labels (FR-008) fall out naturally.

**Alternatives considered**:
- *`stroke-dasharray` donut technique*: simpler math (no trig), but produces a ring, not
  a filled pie, and per-slice hover targets are trickier to size correctly along a
  stroked circle. Rejected as a needless visual deviation from what was asked for ("pie
  graph").

## Decision 3: Category color assignment

**Decision**: A fixed, hard-coded palette of 8 colors. Category slices (excluding
Leftover) are sorted by name and assigned palette colors by index, wrapping around
(`palette[i % len(palette)]`) if there are more than 8 categories. The Leftover slice
always uses one reserved, distinct color (not part of the rotating palette).

**Rationale**: Deterministic and stable across page loads/cycle changes without storing
per-category color assignments (no new persisted data, matching the spec's Assumptions).
Sorting by name (rather than by amount) keeps a given category's color stable as amounts
change cycle to cycle, which matters more for a page the user checks repeatedly than
color-by-rank would.

**Alternatives considered**:
- *Hash-based color (e.g., hash category name to a hue)*: also deterministic, but harder
  to guarantee visually distinct/accessible colors than a curated fixed palette; rejected
  for a small personal app where a curated 8-color palette is simpler and looks better.
- *User-configurable colors*: explicitly out of scope per spec Assumptions.

## Decision 4: Zero-size and single-slice edge cases

**Decision**:
- Any slice (category or Leftover) whose amount is exactly 0 is omitted entirely — this
  already applies to categories per FR-002 ("nonzero total"); the same rule is applied
  to the Leftover slice for consistency (a $0 leftover cycle shows only category
  slices, no zero-width Leftover sliver).
- If exactly one slice remains after omitting zero-amount slices, it is rendered as a
  full circle (`<circle>`) rather than a 360° arc path — an SVG `A` (arc) command cannot
  represent a full 360° sweep (start point and end point coincide, producing a
  degenerate/invisible path), which is a well-known SVG arc limitation.

**Rationale**: Keeps the chart visually correct at both edges (spec Edge Cases: "every
expense falls into a single category" and "no expenses recorded at all").

## Decision 5: Percentage basis when overspent

**Decision**: When the cycle is overspent (`total_expenses > pay_amount`, per FR-009),
slice percentages are computed against `total_expenses` (categories only, summing to
100%) rather than against `pay_amount`, since no Leftover slice is drawn in that case.
In the normal (non-overspent) case, percentages are computed against `pay_amount`
(categories + Leftover summing to 100%).

**Rationale**: Directly required by FR-009 (omit the leftover slice when overspent) —
if percentages stayed anchored to `pay_amount` the category slices would only sum to
less than a full circle, leaving a visually blank gap with nothing to explain it. Basing
percentages on `total_expenses` in that case keeps the pie always visually complete.

**Alternatives considered**:
- *Always base percentages on `pay_amount`, leaving a gap when overspent*: rejected —
  an unexplained gap is more confusing than informative, and the spec's chosen
  resolution (Question 2 answer) was to replace the leftover slice with text, not to
  leave a hole in the pie.
