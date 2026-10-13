# Contract: Configuration and CLI

## Environment variables (app)

| Variable | Required | Meaning |
|---|---|---|
| `BUDGET_DATABASE_URL` | no | libpq conninfo / URL. If unset, libpq's standard `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE` apply. |
| `BUDGET_SECRET_KEY`, `BUDGET_ENV`, `BUDGET_TRUST_PROXY` | as today | unchanged |
| `BUDGET_DB_PATH` | removed | SQLite is no longer used anywhere |
| `BUDGET_TEST_DATABASE_URL` | tests | default `postgresql://localhost/budget_test` |

Startup rules: connect with `connect_timeout=30`; if the connection fails or migrations fail,
`create_app` raises and the process exits (no fallback to a local file — FR-002). In
development, `scripts/dev-server.sh` sets `BUDGET_DATABASE_URL=postgresql://localhost/budget_dev`.

## CLI

The `claim-legacy` command is removed. No new commands.

## Routes

No route, template, or response changes.
