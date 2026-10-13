"""Sign-in, registration, and sign-out (Flask glue over accounts.py and db.py).

The standard Flask extensions do the heavy lifting: Flask-Login (sessions),
Flask-WTF (CSRF), Flask-Limiter (rate limiting). Budget routes live in a separate
blueprint (routes.py) that requires login for everything in it.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_wtf.csrf import CSRFProtect

from budget import db
from budget.accounts import (
    hash_password,
    normalize_email,
    validate_email,
    validate_password,
    verify_password,
)
from budget.app import get_db
from budget.models import User, ValidationError

GENERIC_LOGIN_ERROR = "Invalid email or password."
RATE_LIMITED_ERROR = "Too many attempts. Try again later."

login_manager = LoginManager()
login_manager.login_view = "auth.login"

csrf = CSRFProtect()

# Counters live in memory (single gunicorn worker); they reset on restart.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

bp = Blueprint("auth", __name__)


@login_manager.user_loader  # type: ignore[untyped-decorator]
def load_user(user_id: str) -> User | None:
    return db.get_user(get_db(), int(user_id))


def safe_next_url(target: str) -> str:
    """Only same-site relative paths are honoured after sign-in."""
    home = url_for("budget.leftover")
    if not target or not target.startswith("/") or target.startswith("//"):
        return home
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or "\\" in target:
        return home
    return target


def _email_key() -> str:
    email = normalize_email(request.form.get("email", ""))
    return email or get_remote_address()


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per 15 minutes", methods=["POST"])
@limiter.limit("5 per 15 minutes", key_func=_email_key, methods=["POST"])
def login() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("budget.leftover"))
    next_url = request.values.get("next", "")
    if request.method == "GET":
        return render_template("login.html", error=None, email="", next_url=next_url)

    email = normalize_email(request.form.get("email", ""))
    password = request.form.get("password", "")
    found = db.get_user_with_hash(get_db(), email)
    if found is not None and verify_password(found[1], password):
        user = found[0]
        session.clear()  # fresh session at sign-in
        session.permanent = True
        login_user(user)
        current_app.logger.info("sign-in succeeded: %s from %s", user.email, request.remote_addr)
        return redirect(safe_next_url(next_url))

    current_app.logger.warning("sign-in failed: %s from %s", email, request.remote_addr)
    return render_template(
        "login.html", error=GENERIC_LOGIN_ERROR, email=email, next_url=next_url
    )


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def register() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("budget.leftover"))
    if request.method == "GET":
        return render_template("register.html", error=None, email="")

    email = normalize_email(request.form.get("email", ""))
    password = request.form.get("password", "")
    try:
        validate_email(email)
        validate_password(password)
        if password != request.form.get("password_confirm", ""):
            raise ValidationError("Passwords do not match")
        new_id = db.create_user(get_db(), email, hash_password(password))
    except ValidationError as exc:
        return render_template("register.html", error=str(exc), email=email)

    session.clear()
    session.permanent = True
    login_user(User(id=new_id, email=email))
    current_app.logger.info("registered: %s from %s", email, request.remote_addr)
    return redirect(url_for("budget.leftover"))


@bp.app_errorhandler(429)
def rate_limited(_error: Exception) -> ResponseReturnValue:
    current_app.logger.warning(
        "rate limited: %s from %s", request.path, request.remote_addr
    )
    template = "register.html" if request.endpoint == "auth.register" else "login.html"
    return (
        render_template(template, error=RATE_LIMITED_ERROR, email="", next_url=""),
        429,
    )


@bp.route("/logout", methods=["POST"])
def logout() -> ResponseReturnValue:
    if current_user.is_authenticated:
        current_app.logger.info("sign-out: %s", current_user.email)
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/healthz")
def healthz() -> str:
    return "ok"
