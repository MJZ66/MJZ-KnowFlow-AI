"""Tests for knowledge base member invite by email."""

from __future__ import annotations

from tests.e2e_helpers import make_api_client, unique_user


def test_add_member_by_email():
    owner = unique_user()
    member = unique_user()

    member_client = make_api_client()
    try:
        member_reg = member_client.post("/api/auth/register", json=member)
        assert member_reg.status_code == 201, member_reg.text
    finally:
        member_client.close()

    owner_client = make_api_client()
    try:
        owner_reg = owner_client.post("/api/auth/register", json=owner)
        assert owner_reg.status_code == 201, owner_reg.text

        kb = owner_client.post(
            "/api/kbs",
            json={"name": "Team KB", "description": "", "visibility": "private"},
        )
        assert kb.status_code == 201, kb.text
        kb_id = kb.json()["id"]

        invite = owner_client.post(
            f"/api/kbs/{kb_id}/members",
            json={"email": member["email"], "role": "viewer"},
        )
        assert invite.status_code == 201, invite.text
        body = invite.json()
        assert body["email"] == member["email"]
        assert body["username"] == member["username"]
        assert body["role"] == "viewer"

        listed = owner_client.get(f"/api/kbs/{kb_id}/members")
        assert listed.status_code == 200, listed.text
        emails = {m["email"] for m in listed.json()}
        assert member["email"] in emails
    finally:
        owner_client.close()
