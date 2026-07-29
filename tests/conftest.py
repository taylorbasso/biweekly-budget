from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from budget.app import create_app


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite3"


@pytest.fixture
def app(db_path: Path) -> Flask:
    return create_app(db_path)


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
