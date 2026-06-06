"""Tests for document chunk preview API."""

from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from tests.e2e_helpers import (
    make_api_client,
    make_chinese_txt,
    poll_document,
    unique_user,
)

# Valid 1x1 PNG
MINI_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture(scope="module")
def api_client():
    client = make_api_client()
    yield client
    client.close()


def test_document_chunks_preview(api_client: httpx.Client, tmp_path: Path):
    user = unique_user()
    reg = api_client.post("/api/auth/register", json=user)
    assert reg.status_code == 201

    kb = api_client.post("/api/kbs", json={
        "name": "Preview KB",
        "description": "",
        "visibility": "private",
    }).json()

    txt = tmp_path / "preview.txt"
    make_chinese_txt(txt)
    with txt.open("rb") as f:
        doc = api_client.post(
            f"/api/kbs/{kb['id']}/documents/upload",
            files={"file": ("preview.txt", f, "text/plain")},
        ).json()

    status = poll_document(api_client, doc["id"])
    assert status["status"] == "completed"

    r = api_client.get(f"/api/documents/{doc['id']}/chunks")
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"] == doc["id"]
    assert len(body["chunks"]) > 0
    assert "content" in body["chunks"][0]
    assert body.get("preview_kind") == "text"
    assert body.get("file_type") == "txt"


def test_document_file_download_and_image_preview(api_client: httpx.Client):
    user = unique_user()
    reg = api_client.post("/api/auth/register", json=user)
    assert reg.status_code == 201

    kb = api_client.post("/api/kbs", json={
        "name": "Image Preview KB",
        "description": "",
        "visibility": "private",
    }).json()

    doc = api_client.post(
        f"/api/kbs/{kb['id']}/documents/upload",
        files={"file": ("sample.png", MINI_PNG, "image/png")},
    ).json()

    status = poll_document(api_client, doc["id"])
    assert status["status"] == "completed"

    chunks = api_client.get(f"/api/documents/{doc['id']}/chunks")
    assert chunks.status_code == 200
    body = chunks.json()
    assert body["preview_kind"] == "image"
    assert body["file_type"] == "png"
    assert len(body["chunks"]) > 0

    file_resp = api_client.get(f"/api/documents/{doc['id']}/file")
    assert file_resp.status_code == 200
    assert file_resp.headers.get("content-type", "").startswith("image/")
    assert file_resp.content.startswith(b"\x89PNG")


def test_document_chunks_forbidden_without_access(tmp_path: Path):
    owner = unique_user()
    other = unique_user()

    doc_id: int
    owner_client = make_api_client()
    try:
        owner_client.post("/api/auth/register", json=owner)
        kb = owner_client.post("/api/kbs", json={
            "name": "Private Preview KB",
            "description": "",
            "visibility": "private",
        }).json()

        txt = tmp_path / "private.txt"
        make_chinese_txt(txt)
        with txt.open("rb") as f:
            doc = owner_client.post(
                f"/api/kbs/{kb['id']}/documents/upload",
                files={"file": ("private.txt", f, "text/plain")},
            ).json()
        doc_id = doc["id"]

        poll_document(owner_client, doc_id)
    finally:
        owner_client.close()

    other_client = make_api_client()
    try:
        other_client.post("/api/auth/register", json=other)
        r = other_client.get(f"/api/documents/{doc_id}/chunks")
        assert r.status_code in (403, 404)
    finally:
        other_client.close()
