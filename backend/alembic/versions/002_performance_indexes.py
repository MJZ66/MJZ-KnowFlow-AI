"""Performance indexes for documents and chunks.

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_kb_status",
        "documents",
        ["knowledge_base_id", "status"],
    )
    op.create_index(
        "ix_documents_status",
        "documents",
        ["status"],
    )
    op.create_index(
        "ix_document_chunks_kb_doc_index",
        "document_chunks",
        ["knowledge_base_id", "document_id", "chunk_index"],
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_kb_doc_index", table_name="document_chunks")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_kb_status", table_name="documents")
