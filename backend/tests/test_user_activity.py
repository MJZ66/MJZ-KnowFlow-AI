"""Unit tests for user presence helpers (no DB)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services import user_activity


def test_is_user_online_within_threshold(monkeypatch):
    monkeypatch.setattr(user_activity, "online_threshold_minutes", lambda: 5)
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
    u = SimpleNamespace(last_active_at=now - timedelta(minutes=2))
    assert user_activity.is_user_online(u, now=now) is True


def test_is_user_offline_when_stale(monkeypatch):
    monkeypatch.setattr(user_activity, "online_threshold_minutes", lambda: 5)
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
    u = SimpleNamespace(last_active_at=now - timedelta(minutes=10))
    assert user_activity.is_user_online(u, now=now) is False


def test_touch_activity_throttled():
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
    u = SimpleNamespace(last_active_at=now - timedelta(seconds=30))
    assert user_activity.should_touch_activity(u, now=now) is False
    u.last_active_at = now - timedelta(seconds=90)
    assert user_activity.should_touch_activity(u, now=now) is True
