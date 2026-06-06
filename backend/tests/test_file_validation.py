"""Upload validation regression tests — especially PDF edge cases."""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.services.file_validation import validate_upload_file, _has_pdf_signature, ZIP_SIGNATURE


def test_pdf_signature_with_leading_whitespace():
    content = b"   \n%PDF-1.4 test"
    assert _has_pdf_signature(content) is True


def _run(coro):
    return asyncio.run(coro)


def test_validate_pdf_with_leading_whitespace():
    content = b"  \r\n%PDF-1.4\n1 0 obj"
    file = UploadFile(filename="report.pdf", file=io.BytesIO(content))
    file.headers = {"content-type": "application/pdf"}

    async def run():
        return await validate_upload_file(file)

    ext, body, name = _run(run())
    assert ext == "pdf"
    assert body.startswith(b"  ")
    assert name.endswith(".pdf")


def test_validate_pdf_accepts_x_pdf_mime():
    content = b"%PDF-1.4\n"
    file = UploadFile(filename="scan.pdf", file=io.BytesIO(content))
    file.headers = {"content-type": "application/x-pdf"}

    async def run():
        return await validate_upload_file(file)

    ext, _, _ = _run(run())
    assert ext == "pdf"


def test_validate_pdf_accepts_octet_stream_when_magic_matches():
    content = b"%PDF-1.4\n"
    file = UploadFile(filename="file.pdf", file=io.BytesIO(content))
    file.headers = {"content-type": "application/octet-stream"}

    async def run():
        return await validate_upload_file(file)

    ext, _, _ = _run(run())
    assert ext == "pdf"


def test_validate_rejects_non_pdf_content():
    content = b"not a pdf file"
    file = UploadFile(filename="fake.pdf", file=io.BytesIO(content))

    async def run():
        return await validate_upload_file(file)

    with pytest.raises(HTTPException) as exc:
        _run(run())
    assert exc.value.status_code == 400


def test_validate_xlsx_zip_magic():
    content = ZIP_SIGNATURE + b"fake xlsx content"
    file = UploadFile(filename="data.xlsx", file=io.BytesIO(content))
    file.headers = {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    async def run():
        return await validate_upload_file(file)

    ext, _, name = _run(run())
    assert ext == "xlsx"
    assert name.endswith(".xlsx")


def test_validate_png_magic():
    # Minimal PNG header (not a valid full image but passes magic check in tests - actually validation needs full PNG header)
    content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    file = UploadFile(filename="photo.png", file=io.BytesIO(content))
    file.headers = {"content-type": "image/png"}

    async def run():
        return await validate_upload_file(file)

    ext, _, _ = _run(run())
    assert ext == "png"

