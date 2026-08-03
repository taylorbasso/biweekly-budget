#!/usr/bin/env bash
# Run the test suite and static type check — the two gates required before a
# change is considered done (constitution Principles III and V).
set -euo pipefail

cd "$(dirname "$0")/.."

source .venv/bin/activate

echo "==> pytest"
pytest tests/

echo "==> mypy"
mypy src/
