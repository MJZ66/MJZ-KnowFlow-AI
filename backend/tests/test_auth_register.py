"""Regression: auth register persists lowercase userrole after enum normalization."""

from __future__ import annotations

import httpx
import pytest

from tests.e2e_helpers import BASE, TIMEOUT, make_api_client, register_user, unique_user


@pytest.fixture(scope="module")
def api_client():
    client = make_api_client()
    yield client
    client.close()


def test_register_sets_auth_cookies(api_client: httpx.Client):
    user = register_user(api_client)
    me = api_client.get(f"{BASE}/api/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["email"] == user["email"]


def test_register_duplicate_email_returns_409(api_client: httpx.Client):
    user = unique_user()
    first = api_client.post(f"{BASE}/api/auth/register", json=user)
    assert first.status_code == 201, first.text

    second = api_client.post(f"{BASE}/api/auth/register", json=user)
    assert second.status_code == 409
    assert second.json().get("code") == "AUTH_EMAIL_EXISTS"


def test_refresh_rotates_cookie_session(api_client: httpx.Client):
    register_user(api_client)
    refresh = api_client.post(f"{BASE}/api/auth/refresh", json={})
    assert refresh.status_code == 200, refresh.text
    assert api_client.get(f"{BASE}/api/auth/me").status_code == 200


def test_logout_clears_cookie_session(api_client: httpx.Client):
    register_user(api_client)
    assert api_client.get(f"{BASE}/api/auth/me").status_code == 200
    assert api_client.post(f"{BASE}/api/auth/logout").status_code == 200
    assert api_client.get(f"{BASE}/api/auth/me").status_code == 401
