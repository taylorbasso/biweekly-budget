# Contract: Configuration and CLI

## Environment variables (app)

| Variable | Required | Meaning |
|---|---|---|
| `BUDGET_DATABASE_URL` | no | libpq conninfo / URL. If unset, libpq's standard `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE` apply. |
| `BUDGET_SECRET_KEY`, `BUDGET_ENV`, `BUDGET_TRUST_PROXY` | as today | unchanged |
| `BUDGET_DB_PATH` | removed | SQLite path; only the importer's `--path` still takes a SQLite file |
| `BUDGET_TEST_DATABASE_URL` | tests | default `postgresql://localhost/budget_test` |

Startup rules: connect with `connect_timeout=30`; if the connection fails or migrations fail,
`create_app` raises and the process exits (no fallback to a local file — FR-002). In
development, `scripts/dev-server.sh` sets `BUDGET_DATABASE_URL=postgresql://localhost/budget_dev`.

## CLI (Flask)

```text
flask --app src.budget.app claim-legacy --email EMAIL     # unchanged behavior
flask --app src.budget.app import-sqlite --path FILE [--replace]
```

`import-sqlite` exit codes: 0 = copied and verified; 1 = rejected data, mismatch, or non-empty
target without `--replace`. Output: one line per table (`table: source N / target N`) and one per
account (`email: leftover source X / target Y`).

## Routes

No route, template, or response changes.
