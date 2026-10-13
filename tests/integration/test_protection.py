from __future__ import annotations

import re

from flask import Flask


def test_every_budget_route_requires_login(app: Flask) -> None:
    client = app.test_client()
    checked = 0
    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith("budget."):
            continue
        path = re.sub(r"<(?:\w+:)?\w+>", "1", rule.rule)
        for method in sorted((rule.methods or set()) & {"GET", "POST"}):
            response = client.open(path, method=method)
            assert response.status_code == 302, (method, path)
            assert response.headers["Location"].startswith("/login"), (method, path)
            checked += 1
    assert checked >= 20


def test_login_and_health_check_are_public(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/login").status_code == 200
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.get_data(as_text=True) == "ok"


def test_unauthenticated_redirect_carries_original_path(app: Flask) -> None:
    response = app.test_client().get("/expenses")
    assert response.headers["Location"] == "/login?next=%2Fexpenses"
