"""User login/activity timestamps and online status helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.models import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def online_threshold_minutes() -> int:
    return max(1, get_settings().USER_ONLINE_THRESHOLD_MINUTES)


def is_user_online(user: User, *, now: datetime | None = None) -> bool:
    """User is online if last_active_at is within the configured window."""
    if user.last_active_at is None:
        return False
    now = now or utcnow()
    active = user.last_active_at
    if active.tzinfo is None:
        active = active.replace(tzinfo=timezone.utc)
    return (now - active) <= timedelta(minutes=online_threshold_minutes())


def should_touch_activity(user: User, *, now: datetime | None = None) -> bool:
    """Throttle activity writes to at most once per minute."""
    if user.last_active_at is None:
        return True
    now = now or utcnow()
    active = user.last_active_at
    if active.tzinfo is None:
        active = active.replace(tzinfo=timezone.utc)
    return (now - active) >= timedelta(seconds=60)


def record_login(user: User, *, now: datetime | None = None) -> None:
    now = now or utcnow()
    user.last_login_at = now
    user.last_active_at = now


def touch_activity(user: User, *, now: datetime | None = None) -> bool:
    """Update last_active_at if throttling allows. Returns True if updated."""
    if not should_touch_activity(user, now=now):
        return False
    user.last_active_at = now or utcnow()
    return True
