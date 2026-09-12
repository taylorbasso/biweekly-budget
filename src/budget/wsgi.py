from __future__ import annotations

import os

from budget.app import create_app

app = create_app(os.environ.get("BUDGET_DB_PATH", "/data/budget.sqlite3"))
