from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, current_app, g

from budget import db


def create_app(db_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    if db_path is None:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        db_path = Path(app.instance_path) / "budget.sqlite3"
    app.config["DATABASE"] = str(db_path)

    with app.app_context():
        conn = db.connect(app.config["DATABASE"])
        db.init_db(conn)
        conn.close()

    app.teardown_appcontext(_close_db)

    from budget.routes import bp

    app.register_blueprint(bp)

    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = db.connect(current_app.config["DATABASE"])
    return g.db  # type: ignore[no-any-return]


def _close_db(exception: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
