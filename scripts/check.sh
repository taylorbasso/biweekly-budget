#!/usr/bin/env bash
# Run the test suite and static type check — the two gates required before a
# change is considered done (constitution Principles III and V).
set -euo pipefail

cd "$(dirname "$0")/.."

source .venv/bin/activate

export PGDATABASE="${PGDATABASE:-budget_test}"
python -c "import psycopg; psycopg.connect('', connect_timeout=3).close()" 2>/dev/null \
  || { echo "PostgreSQL not reachable (database $PGDATABASE). Start it: brew services start postgresql@16" >&2; exit 1; }

echo "==> pytest"
pytest tests/

echo "==> mypy"
mypy src/
