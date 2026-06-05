"""Detect automated / E2E test accounts for admin filtering and cleanup."""

from __future__ import annotations

from sqlalchemy import ColumnElement, or_

from app.models import User

TEST_EMAIL_SUFFIX = "@example.com"
TEST_PREFIXES = ("e2e_", "rq_", "pw_", "pwd_")


def is_test_account(*, email: str, username: str) -> bool:
    email_l = (email or "").strip().lower()
    username_l = (username or "").strip().lower()
    if email_l.endswith(TEST_EMAIL_SUFFIX):
        return True
    return any(
        email_l.startswith(p) or username_l.startswith(p) for p in TEST_PREFIXES
    )


def test_account_sql_clause() -> ColumnElement[bool]:
    """SQL expression matching is_test_account (for queries)."""
    clauses = [User.email.ilike(f"%{TEST_EMAIL_SUFFIX}")]
    for prefix in TEST_PREFIXES:
        clauses.append(User.email.ilike(f"{prefix}%"))
        clauses.append(User.username.ilike(f"{prefix}%"))
    return or_(*clauses)
