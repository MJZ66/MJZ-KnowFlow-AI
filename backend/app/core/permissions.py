"""
Knowledge base permission checking utilities.
Ensures backend-enforced access control beyond frontend UI restrictions.
"""

from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeBase, KnowledgeBaseMember, User


class KBAccessLevel(str, Enum):
    """Access level for a user on a knowledge base."""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    NONE = "none"  # no access at all


async def get_kb_access_level(
    db: AsyncSession, kb_id: int, user: User
) -> KBAccessLevel:
    """Determine the effective access level of a user for a knowledge base.

    Returns the highest applicable role:
    - OWNER if user created the KB
    - Member role (editor/viewer) if explicitly added
    - VIEWER if KB is public
    - NONE otherwise
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    if kb is None:
        return KBAccessLevel.NONE

    # Owner always has full access
    if kb.user_id == user.id:
        return KBAccessLevel.OWNER

    # Check explicit membership
    member_result = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == user.id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member:
        return KBAccessLevel(member.role.value if hasattr(member.role, 'value') else member.role)

    # Public KBs are viewable by anyone
    kb_vis = kb.visibility.value if hasattr(kb.visibility, 'value') else kb.visibility
    if kb_vis == "public":
        return KBAccessLevel.VIEWER

    return KBAccessLevel.NONE


async def require_kb_access(
    db: AsyncSession,
    kb_id: int,
    user: User,
    minimum_role: KBAccessLevel = KBAccessLevel.VIEWER,
) -> KnowledgeBase:
    """Require at least `minimum_role` access to a knowledge base.

    Returns the KnowledgeBase if access is granted.
    Raises HTTPException(403) if access is denied.
    Raises HTTPException(404) if KB not found.

    Role hierarchy: owner > editor > viewer
    """
    from fastapi import HTTPException, status

    level = await get_kb_access_level(db, kb_id, user)

    if level == KBAccessLevel.NONE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found.",
        )

    role_order = {
        KBAccessLevel.OWNER: 3,
        KBAccessLevel.EDITOR: 2,
        KBAccessLevel.VIEWER: 1,
    }

    if role_order.get(level, 0) < role_order.get(minimum_role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires at least '{minimum_role.value}' access.",
        )

    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    return result.scalar_one()
