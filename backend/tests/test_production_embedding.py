"""Production embedding configuration validation."""

from __future__ import annotations

import pytest

from app.core.config import Settings, validate_production_settings


def _prod_settings(**overrides) -> Settings:
    base = dict(
        APP_ENV="production",
        SECRET_KEY="x" * 32,
        EMBEDDING_PROVIDER="local_bge",
        VECTOR_PROVIDER="chroma",
        EMBEDDING_DIM=1024,
    )
    base.update(overrides)
    return Settings(**base)


def test_production_local_bge_rejects_chroma_hash():
    settings = _prod_settings(VECTOR_PROVIDER="chroma_hash")
    with pytest.raises(RuntimeError, match="VECTOR_PROVIDER=chroma"):
        validate_production_settings(settings)


def test_production_hash_logs_warning(caplog):
    settings = _prod_settings(EMBEDDING_PROVIDER="hash", VECTOR_PROVIDER="chroma_hash")
    validate_production_settings(settings)
    assert "EMBEDDING_PROVIDER=hash in production" in caplog.text


def test_production_local_bge_dim_warning(caplog):
    settings = _prod_settings(EMBEDDING_DIM=384)
    validate_production_settings(settings)
    assert "1024 dimensions" in caplog.text
