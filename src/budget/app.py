from __future__ import annotations

import os
import sqlite3
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Any

import click
from flask import Flask, Response, current_app, g, request
from werkzeug.middleware.proxy_fix import ProxyFix

from budget import db
from budget.accounts import normalize_email
from budget.models import ValidationError


DEV_SECRET_KEY = "dev-only-secret-key"


def create_app(
    db_path: str | Path | None = None, config: Mapping[str, Any] | None = None
) -> Flask:
    app = Flask(__name__)
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    development = os.environ.get("BUDGET_ENV", "production") == "development"
    app.config.update(
        SECRET_KEY=os.environ.get("BUDGET_SECRET_KEY")
        or (DEV_SECRET_KEY if development else None),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not development,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    if config is not None:
        app.config.update(config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "BUDGET_SECRET_KEY must be set (or run with BUDGET_ENV=development)"
        )
    if os.environ.get("BUDGET_TRUST_PROXY") == "1":
        # One trusted hop: the ALB. Needed for the client IP and the HTTPS scheme.
        app.wsgi_app = ProxyFix(  # type: ignore[method-assign]
            app.wsgi_app, x_for=1, x_proto=1, x_host=1
        )

    if db_path is None:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        db_path = Path(app.instance_path) / "budget.sqlite3"
    app.config["DATABASE"] = str(db_path)

    with app.app_context():
        conn = db.connect(app.config["DATABASE"])
        db.init_db(conn)
        conn.close()

    app.teardown_appcontext(_close_db)

    app.jinja_env.filters["usd"] = _format_cents_as_usd
    app.jinja_env.filters["payoff"] = _format_payoff_months
    app.jinja_env.filters["utilization"] = _format_utilization_percent

    from budget.auth import bp as auth_bp
    from budget.auth import csrf, limiter, login_manager
    from budget.routes import bp

    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(bp)

    @app.cli.command("claim-legacy")
    @click.option("--email", required=True, help="Email of the existing account to receive the data.")
    def claim_legacy(email: str) -> None:
        """Assign pre-login (unowned) budget data to an existing account."""
        found = db.get_user_with_hash(get_db(), normalize_email(email))
        if found is None:
            raise click.ClickException(f"No account with email {email}")
        try:
            counts = db.claim_legacy_rows(get_db(), found[0].id)
        except ValidationError as exc:
            raise click.ClickException(str(exc)) from exc
        for table, rows in counts.items():
            click.echo(f"{table}: {rows} row(s) assigned to {found[0].email}")

    @app.after_request
    def _no_store(response: Response) -> Response:
        # Keep financial data out of the browser cache (Back after sign-out).
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


def _format_cents_as_usd(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def _format_payoff_months(months: int | None) -> str:
    if months is None:
        return "Never at this rate"
    if months == 0:
        return "Paid off"
    return f"{months} months"


def _format_utilization_percent(percent: float | None) -> str:
    if percent is None:
        return "N/A"
    return f"{percent:.1f}%"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = db.connect(current_app.config["DATABASE"])
    return g.db  # type: ignore[no-any-return]


def _close_db(exception: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
