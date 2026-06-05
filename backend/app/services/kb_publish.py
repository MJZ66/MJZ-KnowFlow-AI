"""Knowledge base publish-to-public approval workflow."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeBase, PublishStatus, User, UserRole, Visibility


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_staff(user: User) -> bool:
    return user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)


def kb_to_public_dict(kb: KnowledgeBase, owner: User | None = None) -> dict:
    vis = kb.visibility.value if hasattr(kb.visibility, "value") else str(kb.visibility)
    pub = kb.publish_status.value if hasattr(kb.publish_status, "value") else str(kb.publish_status)
    return {
        "id": kb.id,
        "user_id": kb.user_id,
        "owner_username": owner.username if owner else None,
        "name": kb.name,
        "description": kb.description or "",
        "visibility": vis,
        "publish_status": pub,
        "publish_requested_at": kb.publish_requested_at.isoformat() if kb.publish_requested_at else None,
        "publish_reviewed_at": kb.publish_reviewed_at.isoformat() if kb.publish_reviewed_at else None,
        "publish_review_note": kb.publish_review_note,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
    }


async def request_publish(
    db: AsyncSession,
    kb: KnowledgeBase,
    user: User,
) -> KnowledgeBase:
    if kb.user_id != user.id and not is_staff(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can request publishing.")

    pub = kb.publish_status
    if hasattr(pub, "value"):
        pub = pub.value
    if pub == PublishStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Publish request is already pending.")
    if kb.visibility == Visibility.PUBLIC and pub == PublishStatus.APPROVED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Knowledge base is already public.")

    kb.publish_status = PublishStatus.PENDING
    kb.publish_requested_at = utcnow()
    kb.publish_review_note = None
    kb.visibility = Visibility.PRIVATE
    await db.flush()
    return kb


async def approve_publish(
    db: AsyncSession,
    kb_id: int,
    admin: User,
    note: str | None = None,
) -> KnowledgeBase:
    kb = await _get_kb(db, kb_id)
    kb.visibility = Visibility.PUBLIC
    kb.publish_status = PublishStatus.APPROVED
    kb.publish_reviewed_at = utcnow()
    kb.publish_reviewed_by = admin.id
    kb.publish_review_note = note
    await db.flush()
    return kb


async def reject_publish(
    db: AsyncSession,
    kb_id: int,
    admin: User,
    note: str | None = None,
) -> KnowledgeBase:
    kb = await _get_kb(db, kb_id)
    kb.visibility = Visibility.PRIVATE
    kb.publish_status = PublishStatus.REJECTED
    kb.publish_reviewed_at = utcnow()
    kb.publish_reviewed_by = admin.id
    kb.publish_review_note = note
    await db.flush()
    return kb


async def _get_kb(db: AsyncSession, kb_id: int) -> KnowledgeBase:
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if kb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found.")
    return kb
