"""Tests for knowledge base member invite by email."""

from __future__ import annotations

import httpx
import pytest

from tests.e2e_helpers import BASE, TIMEOUT, auth_headers, unique_user


@pytest.fixture(scope="module")
def api_client():
    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        yield client


def test_add_member_by_email(api_client: httpx.Client):
    owner = unique_user()
    member = unique_user()

    owner_reg = api_client.post("/api/auth/register", json=owner)
    assert owner_reg.status_code == 201, owner_reg.text
    owner_headers = auth_headers(owner_reg.json()["access_token"])

    member_reg = api_client.post("/api/auth/register", json=member)
    assert member_reg.status_code == 201, member_reg.text

    kb = api_client.post(
        "/api/kbs",
        headers=owner_headers,
        json={"name": "Team KB", "description": "", "visibility": "private"},
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    invite = api_client.post(
        f"/api/kbs/{kb_id}/members",
        headers=owner_headers,
        json={"email": member["email"], "role": "viewer"},
    )
    assert invite.status_code == 201, invite.text
    body = invite.json()
    assert body["email"] == member["email"]
    assert body["username"] == member["username"]
    assert body["role"] == "viewer"

    listed = api_client.get(f"/api/kbs/{kb_id}/members", headers=owner_headers)
    assert listed.status_code == 200, listed.text
    emails = {m["email"] for m in listed.json()}
    assert member["email"] in emails
