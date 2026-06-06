"""Pytest acceptance tests — migrated from scripts/e2e_acceptance.py."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tests.conftest import requires_llm
from tests.e2e_helpers import (
    BASE,
    TIMEOUT,
    auth_headers,
    make_chinese_txt,
    parse_sse_stream,
    poll_document,
    unique_user,
)


@pytest.fixture(scope="module")
def api_client():
    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        yield client


@pytest.fixture(scope="module")
def auth_ctx(api_client: httpx.Client):
    user = unique_user()
    r = api_client.post("/api/auth/register", json=user)
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"headers": auth_headers(token), "user": user}


def test_health(api_client: httpx.Client):
    r = api_client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def _register_password_test_user(api_client: httpx.Client) -> dict:
    user = unique_user()
    reg = api_client.post("/api/auth/register", json=user)
    assert reg.status_code == 201, reg.text
    return {
        "user": user,
        "headers": auth_headers(reg.json()["access_token"]),
    }


def test_change_password(api_client: httpx.Client):
    ctx = _register_password_test_user(api_client)
    user = ctx["user"]
    headers = ctx["headers"]
    new_password = "NewPass456!"

    r = api_client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": user["password"], "new_password": new_password},
    )
    assert r.status_code == 200, r.text
    assert "updated" in r.json().get("message", "").lower()

    login_new = api_client.post("/api/auth/login", json={
        "email": user["email"],
        "password": new_password,
    })
    assert login_new.status_code == 200

    login_old = api_client.post("/api/auth/login", json={
        "email": user["email"],
        "password": user["password"],
    })
    assert login_old.status_code == 401


def test_change_password_wrong_current(api_client: httpx.Client):
    ctx = _register_password_test_user(api_client)
    r = api_client.post(
        "/api/auth/change-password",
        headers=ctx["headers"],
        json={"current_password": "wrong-password", "new_password": "AnotherPass1!"},
    )
    assert r.status_code == 401
    body = r.json()
    assert body.get("code") == "AUTH_WRONG_CURRENT_PASSWORD"


def test_change_password_same_as_current(api_client: httpx.Client):
    ctx = _register_password_test_user(api_client)
    user = ctx["user"]
    r = api_client.post(
        "/api/auth/change-password",
        headers=ctx["headers"],
        json={"current_password": user["password"], "new_password": user["password"]},
    )
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") == "AUTH_PASSWORD_UNCHANGED"


def test_unified_error_format(api_client: httpx.Client, auth_ctx):
    user = auth_ctx["user"]
    r = api_client.post("/api/auth/login", json={
        "email": user["email"],
        "password": "wrong-password",
    })
    assert r.status_code == 401
    body = r.json()
    assert "code" in body and "message" in body and "message_en" in body


def test_create_kb(api_client: httpx.Client, auth_ctx):
    r = api_client.post("/api/kbs", headers=auth_ctx["headers"], json={
        "name": "Pytest KB",
        "description": "test",
        "visibility": "private",
    })
    assert r.status_code == 201
    assert "id" in r.json()


def test_chinese_upload_completed(api_client: httpx.Client, auth_ctx, tmp_path: Path):
    kb = api_client.post("/api/kbs", headers=auth_ctx["headers"], json={
        "name": "Upload Test KB",
        "description": "",
        "visibility": "private",
    }).json()

    txt = tmp_path / "中文测试.txt"
    make_chinese_txt(txt)
    with txt.open("rb") as f:
        r = api_client.post(
            f"/api/kbs/{kb['id']}/documents/upload",
            headers=auth_ctx["headers"],
            files={"file": ("中文测试文档.txt", f, "text/plain")},
        )
    assert r.status_code == 201
    doc_id = r.json()["id"]
    status = poll_document(api_client, doc_id, auth_ctx["headers"])
    assert status["status"] == "completed"
    assert status.get("progress") == 100


def test_empty_upload_failed(api_client: httpx.Client, auth_ctx, tmp_path: Path):
    kb = api_client.post("/api/kbs", headers=auth_ctx["headers"], json={
        "name": "Fail Test KB",
        "description": "",
        "visibility": "private",
    }).json()

    empty = tmp_path / "empty.txt"
    empty.write_text("   \n\n  ", encoding="utf-8")
    with empty.open("rb") as f:
        r = api_client.post(
            f"/api/kbs/{kb['id']}/documents/upload",
            headers=auth_ctx["headers"],
            files={"file": ("空文档.txt", f, "text/plain")},
        )
    assert r.status_code == 201
    status = poll_document(api_client, r.json()["id"], auth_ctx["headers"], timeout_sec=60)
    assert status["status"] == "failed"


@requires_llm
def test_rag_sse_stream(api_client: httpx.Client, auth_ctx, tmp_path: Path):
    kb = api_client.post("/api/kbs", headers=auth_ctx["headers"], json={
        "name": "RAG Test KB",
        "description": "",
        "visibility": "private",
    }).json()

    txt = tmp_path / "rag.txt"
    make_chinese_txt(txt)
    with txt.open("rb") as f:
        doc = api_client.post(
            f"/api/kbs/{kb['id']}/documents/upload",
            headers=auth_ctx["headers"],
            files={"file": ("rag.txt", f, "text/plain")},
        ).json()
    assert poll_document(api_client, doc["id"], auth_ctx["headers"])["status"] == "completed"

    session = api_client.post(
        f"/api/kbs/{kb['id']}/chat/sessions",
        headers=auth_ctx["headers"],
        json={"title": "pytest"},
    ).json()

    with api_client.stream(
        "POST",
        f"/api/chat/sessions/{session['id']}/stream",
        headers=auth_ctx["headers"],
        json={"content": "KnowFlow AI 支持哪些文件格式？", "top_k": 5},
    ) as stream:
        sse_text = "".join(stream.iter_text())

    events = parse_sse_stream(sse_text)
    types = [e[0] for e in events]
    assert "retrieval_start" in types
    assert "retrieval_done" in types
    assert "token" in types
    assert "done" in types

    refs = next((d for t, d in events if t == "references"), [])
    assert isinstance(refs, list)
    if refs:
        previews = " ".join(str(r.get("content_preview", "")) for r in refs)
        assert "知识库" in previews or "PDF" in previews or "KnowFlow" in previews


def test_i18n_key_parity():
    backend_root = Path(__file__).resolve().parents[1]
    root = backend_root.parent / "frontend" / "src" / "i18n" / "locales"
    if not root.exists():
        import pytest
        pytest.skip("frontend locales not available in this runtime")
    zh = json.loads((root / "zh-CN.json").read_text(encoding="utf-8"))
    en = json.loads((root / "en-US.json").read_text(encoding="utf-8"))
    assert set(zh.keys()) == set(en.keys())
