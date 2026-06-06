"""Prometheus /api/metrics endpoint tests."""

import httpx
import pytest

from app.core.config import get_settings


@pytest.fixture
def metrics_client():
    return httpx.Client(base_url="http://localhost:8000", timeout=10.0)


def test_metrics_endpoint_returns_prometheus_text(metrics_client: httpx.Client):
    r = metrics_client.get("/api/metrics")
    if r.status_code == 404:
        pytest.skip("METRICS_ENABLED=false")
    assert r.status_code == 200
    text = r.text
    assert "http_requests_total" in text
    assert "rag_cache_hit_total" in text
    assert "rag_cache_miss_total" in text
    assert "rag_retrieval_total" in text
    assert "document_process_success_total" in text
    assert "celery_task_success_total" in text


def test_metrics_disabled_returns_404(monkeypatch):
    from app.core.config import Settings
    import main

    class Disabled(Settings):
        METRICS_ENABLED: bool = False

    monkeypatch.setattr(main, "settings", Disabled())

    from fastapi.testclient import TestClient

    with TestClient(main.app) as client:
        r = client.get("/api/metrics")
        assert r.status_code == 404


def test_metrics_enabled_setting_default():
    settings = get_settings()
    assert hasattr(settings, "METRICS_ENABLED")
