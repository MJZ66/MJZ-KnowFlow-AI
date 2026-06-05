"""KB publish approval workflow fields.

Revision ID: 004
Revises: 003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

publish_status = sa.Enum(
    "none", "pending", "approved", "rejected",
    name="publishstatus",
)


def upgrade() -> None:
    publish_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "knowledge_bases",
        sa.Column("publish_status", publish_status, nullable=False, server_default="none"),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("publish_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("publish_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("publish_review_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("publish_reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    # Backfill legacy public rows (cast avoids enum label mismatch on some PG installs)
    op.execute(
        """
        UPDATE knowledge_bases
        SET publish_status = CAST('approved' AS publishstatus)
        WHERE CAST(visibility AS VARCHAR) = 'public'
        """
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "publish_reviewed_by")
    op.drop_column("knowledge_bases", "publish_review_note")
    op.drop_column("knowledge_bases", "publish_reviewed_at")
    op.drop_column("knowledge_bases", "publish_requested_at")
    op.drop_column("knowledge_bases", "publish_status")
    publish_status.drop(op.get_bind(), checkfirst=True)
