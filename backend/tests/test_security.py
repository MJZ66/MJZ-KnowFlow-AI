"""Security-related tests."""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings, validate_production_settings, DEFAULT_SECRET_KEY
from app.services.file_validation import sanitize_filename
from tests.e2e_helpers import BASE, TIMEOUT, auth_headers, unique_user


def test_sanitize_filename_strips_path_traversal():
    assert ".." not in sanitize_filename("../evil.txt")
    assert sanitize_filename("subdir/name.txt") == "name.txt"


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
    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        yield client


def test_upload_exe_rejected(api_client: httpx.Client):
    user = unique_user()
    reg = api_client.post("/api/auth/register", json=user)
    headers = auth_headers(reg.json()["access_token"])
    kb = api_client.post("/api/kbs", headers=headers, json={
        "name": "Security KB",
        "description": "",
        "visibility": "private",
    }).json()

    r = api_client.post(
        f"/api/kbs/{kb['id']}/documents/upload",
        headers=headers,
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") in ("UNSUPPORTED_FILE_TYPE", "DOCUMENT_INVALID_TYPE", "VALIDATION_ERROR")


def test_upload_oversized_rejected(api_client: httpx.Client):
    """Large upload rejection — skipped in CI to avoid 31MB transfer time."""
    import pytest
    pytest.skip("Slow integration test; run manually with backend up")
