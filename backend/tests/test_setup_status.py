"""Tests for setup status service."""

from app.core.config import Settings
from app.services.setup_status import build_setup_status, is_secret_configured


def test_is_secret_configured_rejects_placeholder():
    assert is_secret_configured("") is False
    assert is_secret_configured("your_qwen_api_key_here") is False
    assert is_secret_configured("sk-realkey1234567890") is True


def test_build_setup_status_flags_missing_llm():
    s = Settings(
        LLM_API_KEY="your_qwen_api_key_here",
        DEEPSEEK_API_KEY="",
        OCR_ENABLED=True,
    )
    status = build_setup_status(s)
    assert status["ready_for_chat"] is False
    assert any(i["code"] == "llm_key_missing" for i in status["issues"])


def test_build_setup_status_ok_when_llm_configured():
    s = Settings(
        LLM_API_KEY="sk-testconfiguredkey1234567890",
        DEEPSEEK_API_KEY="sk-testdeepseekkey1234567890",
        OCR_ENABLED=False,
    )
    status = build_setup_status(s)
    assert status["ready_for_chat"] is True
    assert status["llm"]["configured"] is True
    assert status["deepseek"]["configured"] is True
