# Quickstart: Validating the Aurora Postgres Migration

## Local

```bash
brew install postgresql@16 && brew services start postgresql@16
createdb budget_dev && createdb budget_test
source .venv/bin/activate && pip install -e '.[dev]'
./scripts/check.sh               # pytest + mypy, all green
./scripts/dev-server.sh restart  # http://127.0.0.1:5001
```
Register, set a pay schedule, add expenses, restart the server: data persists. The Aug 14 example
in `specs/001-pay-cycle-leftover/quickstart.md` gives the same numbers.

## Deployed

1. Push the new image, then `terragrunt apply` in the `biweekly-budget` stack.
2. Register at https://budget.taylorbasso.dev and re-enter your pay schedule and expenses.
3. Redeploy the service: data persists. After ≥5 min idle the next request takes ~15–30 s, then is normal.
4. From a laptop, `psql` to the cluster endpoint times out (not public).

Rollback: redeploy the previous commit's image.
