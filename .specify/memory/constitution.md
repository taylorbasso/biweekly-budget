<!--
Sync Impact Report
Version change: (template, unratified) → 1.0.0
Modified principles: n/a (initial ratification)
Added sections:
  - Core Principles: I. Simplicity First (YAGNI), II. CLI-First, Library-Oriented Design,
    III. Type Safety & Static Checking, IV. Local-First Data Privacy,
    V. Correctness of Financial Calculations (NON-NEGOTIABLE)
  - Core Domain Rules
  - Development Workflow
  - Governance
Removed sections: none (first fill of template placeholders)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check gate is
    generic and reads principles at plan time)
  - .specify/templates/spec-template.md ✅ no changes needed (generic, no
    principle-specific hardcoding)
  - .specify/templates/tasks-template.md ✅ no changes needed (generic, no
    principle-specific hardcoding)
  - .claude/skills/speckit-*/SKILL.md ✅ no agent-specific references found requiring
    updates
Follow-up TODOs: none
-->

# Biweekly Budget Constitution
<!-- A personal budgeting tool that tells you how much free money you have left to spend
between one paycheck and the next. -->

## Core Principles

### I. Simplicity First (YAGNI)
The system MUST start as a CLI tool backed by a local SQLite database. No additional
interface (web UI, GUI, sync service, API) MAY be introduced until the CLI core is
functional and a concrete, stated need for it exists. Every feature MUST serve the core
goal — computing discretionary spending money between pay dates — before speculative
extensions (multi-currency, recurring-transaction templates, multi-user accounts, budget
forecasting, etc.) are considered. When in doubt, ship the smaller thing.

Rationale: this is an early-stage personal project; the fastest path to a useful tool is
a small, focused core. Premature interface or feature work is wasted effort until the
core calculation is proven correct and useful day-to-day.

### II. CLI-First, Library-Oriented Design
Core budget logic (pay-cycle computation, expense-to-cycle matching, leftover-amount
calculation) MUST live in a Python module independent of any interface layer. The CLI
MUST be a thin wrapper over that module: arguments/stdin in, human-readable text to
stdout, errors to stderr. Business logic MUST NOT be embedded directly in CLI command
handlers.

Rationale: keeping the calculation engine separate from the CLI means a future interface
(TUI, web UI, etc.) can be added later without rewriting the logic that has already been
validated — directly supporting Principle I's "CLI now, UI later" trajectory.

### III. Type Safety & Static Checking
All Python code MUST use type hints on public functions, method signatures, and data
models (income entries, expenses, budget categories, cycle results). A static type
checker MUST be run during development and MUST pass with no errors before a change is
considered complete.

Rationale: this tool exists to answer a money question the user will act on. Static
typing catches an entire class of mistakes (wrong types flowing into date/amount math)
before they can produce a wrong answer.

### IV. Local-First Data Privacy
Income, expenses, and category data MUST be stored locally in SQLite. No financial data
MAY be transmitted to any third-party service or network endpoint without explicit,
separate user opt-in for that specific feature. There is no default cloud sync, telemetry,
or external reporting.

Rationale: this is personal financial data. The default posture is that it never leaves
the user's machine unless they specifically choose to send it somewhere.

### V. Correctness of Financial Calculations (NON-NEGOTIABLE)
Any code that determines pay-cycle boundaries, matches an expense's due date to a cycle,
or computes the leftover/discretionary amount MUST have automated tests covering boundary
conditions: the cycle's start date, the day immediately before the next paycheck,
month/year rollovers, and leap years. Every expense MUST be attributed to exactly one
cycle — never zero, never two — so cycles MUST partition time with no gaps and no
overlaps.

Rationale: this calculation is the entire value proposition of the tool. A silently wrong
answer here (double-counting a bill, or dropping one) is worse than the tool not existing,
because the user will make spending decisions based on it.

## Core Domain Rules

- **Income event**: a paycheck with a date and an amount.
- **Expense**: a bill or budget-category item with a due date and an amount.
- **Cycle**: the span from one income event's date up to (but not including) the next
  income event's date. Example: paid Friday July 31 and next paid Friday August 14 → the
  cycle runs July 31 through August 13 inclusive; August 14 belongs to the *next* cycle.
- **Leftover (discretionary) amount** for a cycle = the cycle's paycheck amount minus the
  sum of all expenses whose due date falls within that cycle.
- Cycle boundaries and expense-to-cycle attribution are derived data, not user input —
  they MUST be computed from stored income and expense dates, never hardcoded or manually
  assigned.

## Development Workflow

- A static type checker MUST pass before a change is considered done (Principle III).
- Automated tests covering cycle-boundary and leftover-calculation logic MUST pass before
  a change touching that logic is considered done (Principle V).
- Database schema changes MUST be expressed as migrations tracked in the repository, not
  as ad-hoc manual edits to a developer's local database file.
- New interfaces, dependencies, or stored-data categories that go beyond the CLI +
  SQLite + local-only baseline MUST be justified against Principles I and IV before being
  added.

## Governance

This constitution supersedes any conflicting practice or prior informal convention for
this project. Amendments are made by editing this file directly, updating the Sync Impact
Report at its top, and bumping the version per the policy below.

**Versioning policy** (semantic versioning applied to governance):
- MAJOR: a principle is removed or redefined in a way that is backward-incompatible with
  prior guidance.
- MINOR: a new principle or section is added, or existing guidance is materially expanded.
- PATCH: wording, clarification, or typo fixes with no semantic change.

**Compliance review**: any change to core budget-calculation logic, storage, or the
CLI/library boundary should be checked against the Core Principles above before being
merged. Complexity that violates Principle I (Simplicity First) must be justified in the
relevant plan's Complexity Tracking section rather than added silently.

**Version**: 1.0.0 | **Ratified**: 2026-07-28 | **Last Amended**: 2026-07-28
