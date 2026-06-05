#!/usr/bin/env python3
"""
Remove accumulated E2E/pytest users and related data.
Keeps production accounts (MJZ, seed admin) and the legacy test super-admin (id=1).

Run:
  python scripts/cleanup_test_data.py --dry-run
  python scripts/cleanup_test_data.py
  docker compose exec backend python scripts/cleanup_test_data.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select, update

from app.core.database import async_session
from app.core.security import hash_password
from app.models import (
    ChatMessage,
    ChatSession,
    Document,
    DocumentChunk,
    KnowledgeBase,
    KnowledgeBaseMember,
    OperationLog,
    User,
    UserRole,
)
from app.services.test_account import is_test_account, test_account_sql_clause

KEEP_USER_IDS = {1, 2, 60}  # test super-admin, MJZ, seed admin
KEEP_EMAILS = {"2429448372@qq.com", "admin@knowflow.local", "test2@example.com"}

TEST_SUPER_ADMIN_EMAIL = "test2@example.com"
TEST_SUPER_ADMIN_PASSWORD = "TestPass123!"


async def run(*, dry_run: bool) -> None:
    async with async_session() as session:
        result = await session.execute(select(User))
        all_users = result.scalars().all()

        to_delete: list[User] = []
        for user in all_users:
            if user.id in KEEP_USER_IDS:
                continue
            if user.email.lower() in KEEP_EMAILS:
                continue
            if is_test_account(email=user.email, username=user.username):
                to_delete.append(user)

        print(f"Users to delete: {len(to_delete)}")
        for u in to_delete[:5]:
            print(f"  - id={u.id} {u.username} <{u.email}>")
        if len(to_delete) > 5:
            print(f"  ... and {len(to_delete) - 5} more")

        if dry_run:
            print("Dry run — no changes applied.")
            return

        delete_ids = [u.id for u in to_delete]
        if delete_ids:
            await session.execute(
                update(KnowledgeBase)
                .where(KnowledgeBase.publish_reviewed_by.in_(delete_ids))
                .values(publish_reviewed_by=None)
            )
            await session.execute(
                update(OperationLog)
                .where(OperationLog.user_id.in_(delete_ids))
                .values(user_id=None)
            )

            kb_ids_result = await session.execute(
                select(KnowledgeBase.id).where(KnowledgeBase.user_id.in_(delete_ids))
            )
            kb_ids = [row[0] for row in kb_ids_result.all()]

            if kb_ids:
                doc_ids_result = await session.execute(
                    select(Document.id).where(Document.knowledge_base_id.in_(kb_ids))
                )
                doc_ids = [row[0] for row in doc_ids_result.all()]
                if doc_ids:
                    await session.execute(
                        delete(DocumentChunk).where(DocumentChunk.document_id.in_(doc_ids))
                    )
                await session.execute(delete(Document).where(Document.knowledge_base_id.in_(kb_ids)))
                await session.execute(
                    delete(KnowledgeBaseMember).where(
                        KnowledgeBaseMember.knowledge_base_id.in_(kb_ids)
                    )
                )
                sess_ids = await session.execute(
                    select(ChatSession.id).where(ChatSession.knowledge_base_id.in_(kb_ids))
                )
                session_ids = [row[0] for row in sess_ids.all()]
                if session_ids:
                    await session.execute(
                        delete(ChatMessage).where(ChatMessage.session_id.in_(session_ids))
                    )
                await session.execute(
                    delete(ChatSession).where(ChatSession.knowledge_base_id.in_(kb_ids))
                )
                await session.execute(delete(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))

            await session.execute(delete(User).where(User.id.in_(delete_ids)))
            print(f"Deleted {len(delete_ids)} test users and their knowledge bases.")

        # Promote MJZ to super_admin
        mjz = await session.execute(
            select(User).where(User.email == "2429448372@qq.com")
        )
        mjz_user = mjz.scalar_one_or_none()
        if mjz_user:
            mjz_user.role = UserRole.SUPER_ADMIN
            print(f"Promoted MJZ (id={mjz_user.id}) to super_admin.")

        # Reset legacy test super-admin password (project E2E standard)
        test_user = await session.execute(
            select(User).where(User.email == TEST_SUPER_ADMIN_EMAIL)
        )
        test = test_user.scalar_one_or_none()
        if test:
            test.role = UserRole.SUPER_ADMIN
            test.hashed_password = hash_password(TEST_SUPER_ADMIN_PASSWORD)
            print(
                f"Reset test super-admin password: email={TEST_SUPER_ADMIN_EMAIL} "
                f"username={test.username}"
            )

        await session.commit()

        remaining = await session.execute(
            select(User).where(~test_account_sql_clause())
        )
        real_users = remaining.scalars().all()
        print(f"Remaining non-test users: {len(real_users)}")
        for u in real_users:
            print(f"  id={u.id} {u.username} <{u.email}> role={u.role.value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
