"""Regression: PostgreSQL enums must persist lowercase Python enum values."""

from sqlalchemy.dialects import postgresql
from sqlalchemy import insert

from app.models import (
    DocumentStatus,
    KnowledgeBase,
    MemberRole,
    MessageRole,
    PublishStatus,
    TaskStatus,
    User,
    UserRole,
    Visibility,
)


def _compiled_role(column_values: dict) -> str:
    stmt = insert(User).values(**column_values)
    sql = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    return sql


def test_user_role_persists_lowercase_value():
    sql = _compiled_role(
        {
            "email": "a@example.com",
            "hashed_password": "hash",
            "username": "alice",
            "role": UserRole.USER,
        }
    )
    assert "'user'" in sql
    assert "'USER'" not in sql


def test_visibility_and_publish_status_persist_lowercase_values():
    stmt = insert(KnowledgeBase).values(
        user_id=1,
        name="KB",
        visibility=Visibility.PRIVATE,
        publish_status=PublishStatus.NONE,
    )
    sql = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "'private'" in sql
    assert "'none'" in sql
    assert "'PRIVATE'" not in sql


def test_other_enum_values_are_lowercase():
    assert MemberRole.OWNER.value == "owner"
    assert DocumentStatus.COMPLETED.value == "completed"
    assert MessageRole.ASSISTANT.value == "assistant"
    assert TaskStatus.RUNNING.value == "running"
