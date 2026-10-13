from __future__ import annotations

import re
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from budget.app import create_app
from tests.conftest import TEST_EMAIL, TEST_PASSWORD, login


# --- US1: sign in -------------------------------------------------------------


def test_login_success_redirects_home(app: Flask, user_id: int) -> None:
    client = app.test_client()
    response = client.post("/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert client.get("/").status_code == 200


def test_login_returns_to_requested_page(app: Flask, user_id: int) -> None:
    client = app.test_client()
    response = client.post(
        "/login",
        data={"email": TEST_EMAIL, "password": TEST_PASSWORD, "next": "/expenses"},
    )
    assert response.headers["Location"] == "/expenses"


@pytest.mark.parametrize(
    "target",
    ["https://evil.example", "//evil.example", "javascript:alert(1)", "/\\evil.example"],
)
def test_login_ignores_offsite_next(app: Flask, user_id: int, target: str) -> None:
    response = app.test_client().post(
        "/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD, "next": target}
    )
    assert response.headers["Location"] == "/"


def test_signed_in_user_visiting_login_goes_home(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_login_matches_email_case_and_spaces(app: Flask, user_id: int) -> None:
    response = app.test_client().post(
        "/login", data={"email": "  OWNER@Example.COM ", "password": TEST_PASSWORD}
    )
    assert response.status_code == 302


def test_session_cookie_flags(app: Flask, user_id: int) -> None:
    response = app.test_client().post(
        "/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_responses_are_not_cacheable(logged_in_client: FlaskClient) -> None:
    assert logged_in_client.get("/").headers["Cache-Control"] == "no-store"
    assert logged_in_client.get("/login").headers["Cache-Control"] == "no-store"


def test_production_defaults_require_secure_cookies_and_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BUDGET_ENV", raising=False)
    monkeypatch.delenv("BUDGET_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app(tmp_path / "a.sqlite3")
    app = create_app(tmp_path / "b.sqlite3", {"SECRET_KEY": "x"})
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


# --- US2: generic errors and rate limits --------------------------------------


def _failed_login_page(app: Flask, email: str, password: str) -> str:
    response = app.test_client().post("/login", data={"email": email, "password": password})
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_unknown_email_and_wrong_password_look_identical(app: Flask, user_id: int) -> None:
    wrong_password = _failed_login_page(app, TEST_EMAIL, "not the password!!")
    unknown_email = _failed_login_page(app, "nobody@example.com", TEST_PASSWORD)
    assert "Invalid email or password." in wrong_password

    def normalized(page: str, email: str) -> str:
        page = re.sub(r'name="csrf_token" value="[^"]*"', "CSRF", page)
        return page.replace(email, "EMAIL")

    assert normalized(wrong_password, TEST_EMAIL) == normalized(
        unknown_email, "nobody@example.com"
    )


def test_failed_login_never_echoes_password(app: Flask, user_id: int) -> None:
    page = _failed_login_page(app, TEST_EMAIL, "super-secret-guess")
    assert "super-secret-guess" not in page


def test_oversized_password_is_a_normal_failure(app: Flask, user_id: int) -> None:
    page = _failed_login_page(app, TEST_EMAIL, "x" * 10_000)
    assert "Invalid email or password." in page


def test_gigantic_request_body_is_rejected_by_flask(app: Flask, user_id: int) -> None:
    response = app.test_client().post(
        "/login", data={"email": TEST_EMAIL, "password": "x" * 600_000}
    )
    assert response.status_code == 413


def test_sixth_attempt_for_one_email_is_refused_even_if_correct(
    app: Flask, user_id: int
) -> None:
    client = app.test_client()
    for _ in range(5):
        response = client.post("/login", data={"email": TEST_EMAIL, "password": "wrong password!"})
        assert response.status_code == 200
    refused = client.post("/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert refused.status_code == 429
    assert "Too many attempts. Try again later." in refused.get_data(as_text=True)
    # Still not signed in.
    assert client.get("/").status_code == 302


def test_per_source_limit_applies_across_different_emails(app: Flask, user_id: int) -> None:
    client = app.test_client()
    for i in range(20):
        response = client.post(
            "/login", data={"email": f"user{i}@example.com", "password": "wrong password!"}
        )
        assert response.status_code == 200
    refused = client.post(
        "/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert refused.status_code == 429


# --- US4: registration --------------------------------------------------------

from budget import db  # noqa: E402
from budget.app import get_db  # noqa: E402


def _register(
    client: FlaskClient, email: str, password: str, confirm: str | None = None
) -> TestResponse:
    return client.post(
        "/register",
        data={
            "email": email,
            "password": password,
            "password_confirm": password if confirm is None else confirm,
        },
    )


def _user_exists(app: Flask, email: str) -> bool:
    with app.app_context():
        return db.get_user_with_hash(get_db(), email) is not None


def test_valid_registration_creates_account_and_signs_in(app: Flask) -> None:
    client = app.test_client()
    response = _register(client, "New@Example.com", "a long enough password")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert client.get("/").status_code == 200
    assert _user_exists(app, "new@example.com")
    # And the new credentials work in a fresh browser.
    login(app.test_client(), "new@example.com", "a long enough password")


@pytest.mark.parametrize(
    ("email", "password", "confirm", "message"),
    [
        ("short@example.com", "x" * 11, None, "at least 12"),
        ("long@example.com", "x" * 129, None, "at most 128"),
        ("not-an-email", "a long enough password", None, "valid email"),
        ("mismatch@example.com", "a long enough password", "different password!", "do not match"),
    ],
)
def test_invalid_registration_is_refused_and_stores_nothing(
    app: Flask, email: str, password: str, confirm: str | None, message: str
) -> None:
    response = _register(app.test_client(), email, password, confirm)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert not _user_exists(app, email)


def test_duplicate_email_is_refused_ignoring_case(app: Flask, user_id: int) -> None:
    response = _register(app.test_client(), TEST_EMAIL.upper(), "a long enough password")
    assert response.status_code == 200
    assert "already registered" in response.get_data(as_text=True)


def test_signed_in_user_visiting_register_goes_home(logged_in_client: FlaskClient) -> None:
    assert logged_in_client.get("/register").status_code == 302


def test_registration_requires_csrf_token(tmp_path: Path) -> None:
    csrf_app = create_app(
        tmp_path / "csrf.sqlite3",
        {"TESTING": True, "SECRET_KEY": "k", "SESSION_COOKIE_SECURE": False},
    )
    from budget.auth import limiter

    limiter.reset()
    response = _register(csrf_app.test_client(), "csrf@example.com", "a long enough password")
    assert response.status_code == 400
    assert not _user_exists(csrf_app, "csrf@example.com")


def test_sixth_registration_from_one_source_is_rate_limited(app: Flask) -> None:
    client = app.test_client()
    for i in range(5):
        _register(client, f"person{i}@example.com", "a long enough password", "mismatch")
    refused = _register(client, "extra@example.com", "a long enough password")
    assert refused.status_code == 429
    assert "Too many attempts" in refused.get_data(as_text=True)
    assert not _user_exists(app, "extra@example.com")


def test_login_and_register_pages_render_csrf_field(app: Flask) -> None:
    for path in ("/login", "/register"):
        page = app.test_client().get(path).get_data(as_text=True)
        assert 'name="csrf_token"' in page


# --- US3: sign out and session lifetime ---------------------------------------


def test_logout_ends_the_session(logged_in_client: FlaskClient) -> None:
    assert logged_in_client.get("/").status_code == 200
    response = logged_in_client.post("/logout")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    after = logged_in_client.get("/expenses")
    assert after.status_code == 302
    assert after.headers["Location"].startswith("/login")


def test_logout_requires_post(logged_in_client: FlaskClient) -> None:
    assert logged_in_client.get("/logout").status_code == 405
    assert logged_in_client.get("/").status_code == 200  # still signed in


def test_logout_requires_csrf_token(tmp_path: Path) -> None:
    csrf_app = create_app(
        tmp_path / "csrf.sqlite3",
        {"TESTING": True, "SECRET_KEY": "k", "SESSION_COOKIE_SECURE": False},
    )
    assert csrf_app.test_client().post("/logout").status_code == 400


def test_nav_and_sign_out_only_shown_when_signed_in(
    app: Flask, logged_in_client: FlaskClient
) -> None:
    anonymous = app.test_client().get("/login").get_data(as_text=True)
    assert "Sign out" not in anonymous
    assert 'href="/expenses"' not in anonymous
    signed_in = logged_in_client.get("/").get_data(as_text=True)
    assert "Sign out" in signed_in
    assert TEST_EMAIL in signed_in


def test_session_is_permanent_with_twelve_hour_lifetime(
    app: Flask, logged_in_client: FlaskClient
) -> None:
    from datetime import timedelta

    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=12)
    cookie = logged_in_client.get_cookie("session")
    assert cookie is not None
    assert cookie.expires is not None  # permanent session => has an expiry
