"""Shared pytest fixtures and markers."""

from __future__ import annotations

import os

import pytest

from app.services.setup_status import is_secret_configured


def llm_configured() -> bool:
    return is_secret_configured(os.environ.get("LLM_API_KEY", ""))


requires_llm = pytest.mark.skipif(
    not llm_configured(),
    reason="LLM_API_KEY not configured (CI uses .env.example placeholders)",
)
