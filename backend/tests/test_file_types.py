"""Tests for file type registry and preview classification."""

from app.services.file_types import preview_kind


def test_preview_kind_image():
    assert preview_kind("png") == "image"
    assert preview_kind("jpg") == "image"


def test_preview_kind_pdf():
    assert preview_kind("pdf") == "pdf"


def test_preview_kind_text():
    assert preview_kind("docx") == "text"
    assert preview_kind("xlsx") == "text"
    assert preview_kind("txt") == "text"
