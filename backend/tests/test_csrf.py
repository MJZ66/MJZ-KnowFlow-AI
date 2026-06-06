"""CSRF protection tests."""

from __future__ import annotations

import httpx
import pytest

from tests.e2e_helpers import BASE, TIMEOUT, bootstrap_csrf, csrf_headers, make_api_client, unique_user


@pytest.fixture(scope="module")
def api_client():
    client = make_api_client()
    yield client
    client.close()


def test_csrf_bootstrap_sets_cookie(api_client: httpx.Client):
    token = bootstrap_csrf(api_client)
    assert token
    assert api_client.cookies.get("kf_csrf") == token


def test_mutating_request_without_csrf_rejected():
    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        user = unique_user()
        r = client.post(f"{BASE}/api/auth/register", json=user)
        assert r.status_code == 403
        assert r.json().get("code") == "CSRF_INVALID"


def test_mutating_request_with_csrf_accepted(api_client: httpx.Client):
    user = unique_user()
    r = api_client.post(f"{BASE}/api/auth/register", json=user)
    assert r.status_code == 201, r.text
    me = api_client.get(f"{BASE}/api/auth/me")
    assert me.status_code == 200


def test_bearer_auth_exempt_from_csrf():
    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        user = unique_user()
        # No CSRF — would fail for cookie-only clients
        r = client.post(
            f"{BASE}/api/auth/register",
            json=user,
            headers={"Authorization": "Bearer fake-token-for-exempt-check"},
        )
        # CSRF passes; auth/register proceeds (201 or 409 if duplicate), not CSRF_INVALID
        assert r.json().get("code") != "CSRF_INVALID"
