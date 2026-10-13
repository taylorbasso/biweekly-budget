from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from budget.accounts import hash_password, normalize_email
from budget.app import create_app, get_db
from budget import db
from budget.auth import limiter

TEST_PASSWORD = "correct horse battery"
TEST_EMAIL = "owner@example.com"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite3"


@pytest.fixture
def app(db_path: Path) -> Flask:
    flask_app = create_app(
        db_path,
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
            "SESSION_COOKIE_SECURE": False,
        },
    )
    limiter.reset()
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def make_user(app: Flask, email: str = TEST_EMAIL, password: str = TEST_PASSWORD) -> int:
    """Create an account directly in the database and return its id."""
    with app.app_context():
        return db.create_user(get_db(), normalize_email(email), hash_password(password))


def login(
    client: FlaskClient, email: str = TEST_EMAIL, password: str = TEST_PASSWORD
) -> None:
    response = client.post("/login", data={"email": email, "password": password})
    assert response.status_code == 302, response.get_data(as_text=True)


@pytest.fixture
def user_id(app: Flask) -> int:
    return make_user(app)


@pytest.fixture
def logged_in_client(app: Flask, user_id: int) -> FlaskClient:
    client = app.test_client()
    login(client)
    return client


@pytest.fixture
def new_logged_in_client(app: Flask) -> Callable[[str], tuple[FlaskClient, int]]:
    """Factory: create another account and a client signed in as it."""

    def factory(email: str) -> tuple[FlaskClient, int]:
        new_user_id = make_user(app, email)
        new_client = app.test_client()
        login(new_client, email)
        return new_client, new_user_id

    return factory
