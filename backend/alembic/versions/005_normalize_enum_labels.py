"""Normalize PostgreSQL enum labels to lowercase values.

Revision ID: 005
Revises: 004

Legacy SQLAlchemy installs created uppercase enum labels (USER, PRIVATE, ...).
Alembic migrations and ORM models expect lowercase values (user, private, ...).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUM_RENAMES: dict[str, list[tuple[str, str]]] = {
    "userrole": [
        ("SUPER_ADMIN", "super_admin"),
        ("ADMIN", "admin"),
        ("USER", "user"),
    ],
    "visibility": [
        ("PUBLIC", "public"),
        ("TEAM", "team"),
        ("PRIVATE", "private"),
    ],
    "memberrole": [
        ("VIEWER", "viewer"),
        ("EDITOR", "editor"),
        ("OWNER", "owner"),
    ],
    "documentstatus": [
        ("FAILED", "failed"),
        ("COMPLETED", "completed"),
        ("EMBEDDING", "embedding"),
        ("CHUNKING", "chunking"),
        ("PARSING", "parsing"),
        ("UPLOADED", "uploaded"),
    ],
    "messagerole": [
        ("SYSTEM", "system"),
        ("ASSISTANT", "assistant"),
        ("USER", "user"),
    ],
    "taskstatus": [
        ("FAILED", "failed"),
        ("COMPLETED", "completed"),
        ("RUNNING", "running"),
        ("PENDING", "pending"),
    ],
}


def _rename_enum_labels(conn, enum_name: str, mapping: list[tuple[str, str]]) -> None:
    rows = conn.execute(
        sa.text(
            """
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = :name
            """
        ),
        {"name": enum_name},
    ).fetchall()
    labels = {row[0] for row in rows}
    for old, new in mapping:
        if old in labels and new not in labels:
            conn.execute(sa.text(f"ALTER TYPE {enum_name} RENAME VALUE '{old}' TO '{new}'"))
            labels.remove(old)
            labels.add(new)


def upgrade() -> None:
    conn = op.get_bind()
    for enum_name, mapping in _ENUM_RENAMES.items():
        _rename_enum_labels(conn, enum_name, mapping)


def downgrade() -> None:
    conn = op.get_bind()
    for enum_name, mapping in _ENUM_RENAMES.items():
        for old, new in reversed(mapping):
            _rename_enum_labels(conn, enum_name, [(new, old)])
