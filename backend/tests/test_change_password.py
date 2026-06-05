"""Unit tests for POST /api/auth/change-password (in-process TestClient)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register(client: TestClient, suffix: str) -> tuple[dict, str]:
    email = f"pwd_{suffix}@example.com"
    password = "TestPass123!"
    r = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "username": f"pwd_{suffix}",
    })
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"email": email, "password": password}, token


def test_change_password_success(client: TestClient):
    user_data, token = _register(client, "unit1")
    headers = {"Authorization": f"Bearer {token}"}
    new_password = "NewPass456!"

    r = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": user_data["password"], "new_password": new_password},
    )
    assert r.status_code == 200, r.text
    assert "updated" in r.json()["message"].lower()

    assert client.post("/api/auth/login", json={
        "email": user_data["email"],
        "password": new_password,
    }).status_code == 200

    assert client.post("/api/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"],
    }).status_code == 401


def test_change_password_wrong_current(client: TestClient):
    _, token = _register(client, "unit2")
    r = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrong", "new_password": "AnotherPass1!"},
    )
    assert r.status_code == 401
    assert r.json().get("code") == "AUTH_WRONG_CURRENT_PASSWORD"


def test_change_password_same_as_current(client: TestClient):
    user_data, token = _register(client, "unit3")
    r = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": user_data["password"], "new_password": user_data["password"]},
    )
    assert r.status_code == 400
    assert r.json().get("code") == "AUTH_PASSWORD_UNCHANGED"
