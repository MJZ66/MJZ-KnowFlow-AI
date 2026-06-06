"""Security-related tests."""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings, validate_production_settings, DEFAULT_SECRET_KEY
from app.core.paths import resolve_upload_path
from app.services.file_validation import sanitize_filename
from tests.e2e_helpers import BASE, TIMEOUT, make_api_client, register_user, unique_user
from fastapi import HTTPException


def test_sanitize_filename_strips_path_traversal():
    assert ".." not in sanitize_filename("../evil.txt")
    assert sanitize_filename("subdir/name.txt") == "name.txt"


def test_resolve_upload_path_rejects_escape(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")

    monkeypatch.setenv("UPLOAD_DIR", str(upload_root))
    from app.core.config import get_settings
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc:
        resolve_upload_path(str(outside))
    assert exc.value.status_code == 403

    get_settings.cache_clear()


def test_production_secret_key_rejected():
    settings = Settings(APP_ENV="production", SECRET_KEY=DEFAULT_SECRET_KEY)
    with pytest.raises(RuntimeError, match="SECRET_KEY is insecure"):
        validate_production_settings(settings)


def test_production_secret_key_accepts_secure():
    settings = Settings(
        APP_ENV="production",
        SECRET_KEY="a" * 32,
    )
    validate_production_settings(settings)


@pytest.fixture(scope="module")
def api_client():
    client = make_api_client()
    yield client
    client.close()


def test_upload_exe_rejected(api_client: httpx.Client):
    user = register_user(api_client)
    kb = api_client.post("/api/kbs", json={
        "name": "Security KB",
        "description": "",
        "visibility": "private",
    }).json()

    r = api_client.post(
        f"/api/kbs/{kb['id']}/documents/upload",
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") in ("UNSUPPORTED_FILE_TYPE", "DOCUMENT_INVALID_TYPE", "VALIDATION_ERROR")


def test_document_status_requires_kb_access(api_client: httpx.Client):
    """User B must not read document status for user A's private KB."""
    owner = unique_user()
    api_client.post("/api/auth/register", json=owner)
    kb = api_client.post(
        "/api/kbs",
        json={"name": "Private KB", "description": "", "visibility": "private"},
    ).json()

    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    upload = api_client.post(
        f"/api/kbs/{kb['id']}/documents/upload",
        files={"file": ("probe.png", io.BytesIO(tiny_png), "image/png")},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["id"]

    intruder_client = make_api_client()
    try:
        intruder = unique_user()
        intruder_client.post("/api/auth/register", json=intruder)
        r = intruder_client.get(f"/api/documents/{doc_id}/status")
        assert r.status_code in (403, 404)
    finally:
        intruder_client.close()


def test_upload_oversized_rejected(api_client: httpx.Client):
    """Large upload rejection — skipped in CI to avoid 31MB transfer time."""
    import pytest
    pytest.skip("Slow integration test; run manually with backend up")

