"""
Knowledge Base API routes:
- POST   /api/kbs                              — Create KB
- GET    /api/kbs                              — List user's KBs
- GET    /api/kbs/{kb_id}                      — Get KB detail
- PATCH  /api/kbs/{kb_id}                      — Update KB
- DELETE /api/kbs/{kb_id}                      — Delete KB
- POST   /api/kbs/{kb_id}/members              — Add member
- GET    /api/kbs/{kb_id}/members              — List members
- DELETE /api/kbs/{kb_id}/members/{user_id}    — Remove member
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import KBAccessLevel, require_kb_access
from app.models import KnowledgeBase, KnowledgeBaseMember, User, Visibility, MemberRole
from app.schemas.kb import KBCreate, KBUpdate, KBResponse, MemberAdd, MemberResponse, PaginatedKBList
from app.core.config import get_settings

router = APIRouter(prefix="/api/kbs", tags=["Knowledge Bases"])
settings = get_settings()


@router.post("", response_model=KBResponse, status_code=status.HTTP_201_CREATED)
async def create_kb(
    req: KBCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new knowledge base. The creator becomes the owner."""
    # Check max KBs per user limit
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeBase).where(
            KnowledgeBase.user_id == current_user.id
        )
    )
    kb_count = count_result.scalar()
    if kb_count >= settings.MAX_KBS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.MAX_KBS_PER_USER} knowledge bases per user.",
        )

    kb = KnowledgeBase(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        visibility=Visibility(req.visibility),
    )
    db.add(kb)
    await db.flush()

    # Add creator as owner member
    owner_member = KnowledgeBaseMember(
        knowledge_base_id=kb.id,
        user_id=current_user.id,
        role=MemberRole.OWNER,
    )
    db.add(owner_member)
    await db.flush()

    return kb


@router.get("", response_model=PaginatedKBList)
async def list_kbs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List knowledge bases accessible by the current user (paginated)."""
    # Owned KBs
    owned_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == current_user.id)
    )
    owned = owned_result.scalars().all()

    # KBs where user is a member (excluding owned)
    member_result = await db.execute(
        select(KnowledgeBase)
        .join(KnowledgeBaseMember, KnowledgeBaseMember.knowledge_base_id == KnowledgeBase.id)
        .where(
            KnowledgeBaseMember.user_id == current_user.id,
            KnowledgeBase.user_id != current_user.id,
        )
    )
    member_kbs = member_result.scalars().all()

    # Public KBs not already included
    public_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.visibility == Visibility.PUBLIC,
            KnowledgeBase.user_id != current_user.id,
        )
    )
    public_kbs = public_result.scalars().all()

    # Deduplicate by ID
    seen = set()
    all_kbs = []
    for kb in owned + member_kbs + public_kbs:
        if kb.id not in seen:
            seen.add(kb.id)
            all_kbs.append(kb)

    all_kbs.sort(key=lambda k: k.created_at, reverse=True)
    total = len(all_kbs)
    page = all_kbs[skip : skip + limit]
    return PaginatedKBList(items=page, total=total, skip=skip, limit=limit)


@router.get("/{kb_id}", response_model=KBResponse)
async def get_kb(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge base details (requires at least viewer access)."""
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)
    return kb


@router.patch("/{kb_id}", response_model=KBResponse)
async def update_kb(
    kb_id: int,
    req: KBUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update knowledge base (requires editor or owner access)."""
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.EDITOR)

    if req.name is not None:
        kb.name = req.name
    if req.description is not None:
        kb.description = req.description
    if req.visibility is not None:
        kb.visibility = Visibility(req.visibility)

    await db.flush()
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a knowledge base (owner only)."""
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.OWNER)
    await db.delete(kb)
    await db.flush()
    from app.services.cache_invalidation import invalidate_kb_rag_cache
    await invalidate_kb_rag_cache(kb_id)


# ============================================
# Member management
# ============================================

@router.post("/{kb_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    kb_id: int,
    req: MemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to a knowledge base (owner only)."""
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.OWNER)

    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == req.user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Check if already a member
    existing = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == req.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member.")

    member = KnowledgeBaseMember(
        knowledge_base_id=kb_id,
        user_id=req.user_id,
        role=MemberRole(req.role),
    )
    db.add(member)
    await db.flush()
    return member


@router.get("/{kb_id}/members", response_model=list[MemberResponse])
async def list_members(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all members of a knowledge base (requires viewer access)."""
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)

    result = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id
        )
    )
    return result.scalars().all()


@router.delete("/{kb_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    kb_id: int,
    member_user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a knowledge base (owner only, or self-removal)."""
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.OWNER)

    result = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == member_user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    # Cannot remove the owner
    if member.role == MemberRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the owner.")

    await db.delete(member)
    await db.flush()
