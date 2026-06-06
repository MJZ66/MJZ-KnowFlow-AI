"""Regression: auth register persists lowercase userrole after enum normalization."""

from __future__ import annotations

import httpx
import pytest

from tests.e2e_helpers import BASE, TIMEOUT, unique_user


@pytest.fixture(scope="module")
def api_client():
    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        yield client


def test_register_returns_tokens(api_client: httpx.Client):
    user = unique_user()
    r = api_client.post(f"{BASE}/api/auth/register", json=user)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body.get("access_token")
    assert body.get("refresh_token")


def test_register_duplicate_email_returns_409(api_client: httpx.Client):
    user = unique_user()
    first = api_client.post(f"{BASE}/api/auth/register", json=user)
    assert first.status_code == 201, first.text

    second = api_client.post(f"{BASE}/api/auth/register", json=user)
    assert second.status_code == 409
    assert second.json().get("code") == "AUTH_EMAIL_EXISTS"
