"""
Knowledge Base API routes:
- POST   /api/kbs
- GET    /api/kbs?scope=mine
- GET    /api/kbs/public/catalog
- POST   /api/kbs/{kb_id}/publish-request
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import KBAccessLevel, require_kb_access
from app.models import (
    KnowledgeBase,
    KnowledgeBaseMember,
    User,
    UserRole,
    Visibility,
    PublishStatus,
    MemberRole,
)
from app.schemas.kb import KBCreate, KBUpdate, KBResponse, MemberAdd, MemberResponse, PaginatedKBList


def _serialize_member(member: KnowledgeBaseMember, user: User | None = None) -> MemberResponse:
    role = member.role.value if hasattr(member.role, "value") else str(member.role)
    return MemberResponse(
        id=member.id,
        knowledge_base_id=member.knowledge_base_id,
        user_id=member.user_id,
        role=role,
        username=user.username if user else None,
        email=user.email if user else None,
        created_at=member.created_at,
    )
from app.core.config import get_settings
from app.services.kb_publish import is_staff, kb_to_public_dict, request_publish

router = APIRouter(prefix="/api/kbs", tags=["Knowledge Bases"])
settings = get_settings()


def _serialize_kb(kb: KnowledgeBase, owner: User | None = None) -> KBResponse:
    vis = kb.visibility.value if hasattr(kb.visibility, "value") else str(kb.visibility)
    pub = kb.publish_status.value if hasattr(kb.publish_status, "value") else str(kb.publish_status)
    return KBResponse(
        id=kb.id,
        user_id=kb.user_id,
        name=kb.name,
        description=kb.description or "",
        visibility=vis,
        publish_status=pub,
        publish_requested_at=kb.publish_requested_at,
        publish_reviewed_at=kb.publish_reviewed_at,
        publish_review_note=kb.publish_review_note,
        owner_username=owner.username if owner else None,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


async def _load_owner(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.post("", response_model=KBResponse, status_code=status.HTTP_201_CREATED)
async def create_kb(
    req: KBCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a private knowledge base owned by the current user."""
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

    visibility = Visibility.PRIVATE
    if is_staff(current_user) and req.visibility == Visibility.PUBLIC.value:
        visibility = Visibility.PUBLIC

    kb = KnowledgeBase(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        visibility=visibility,
        publish_status=PublishStatus.APPROVED if visibility == Visibility.PUBLIC else PublishStatus.NONE,
    )
    db.add(kb)
    await db.flush()

    owner_member = KnowledgeBaseMember(
        knowledge_base_id=kb.id,
        user_id=current_user.id,
        role=MemberRole.OWNER,
    )
    db.add(owner_member)
    await db.flush()

    return _serialize_kb(kb, current_user)


@router.get("", response_model=PaginatedKBList)
async def list_my_kbs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List knowledge bases owned by the current user (private libraries)."""
    total = int(
        (
            await db.execute(
                select(func.count())
                .select_from(KnowledgeBase)
                .where(KnowledgeBase.user_id == current_user.id)
            )
        ).scalar()
        or 0
    )
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == current_user.id)
        .order_by(KnowledgeBase.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    owned = result.scalars().all()
    items = [_serialize_kb(kb, current_user) for kb in owned]
    return PaginatedKBList(items=items, total=total, skip=skip, limit=limit)


@router.get("/public/catalog", response_model=PaginatedKBList)
async def list_public_kbs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List approved public knowledge bases from all users."""
    total = int(
        (
            await db.execute(
                select(func.count())
                .select_from(KnowledgeBase)
                .where(
                    KnowledgeBase.visibility == Visibility.PUBLIC,
                    KnowledgeBase.publish_status == PublishStatus.APPROVED,
                )
            )
        ).scalar()
        or 0
    )
    result = await db.execute(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.visibility == Visibility.PUBLIC,
            KnowledgeBase.publish_status == PublishStatus.APPROVED,
        )
        .order_by(KnowledgeBase.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    kbs = result.scalars().all()
    items = []
    for kb in kbs:
        owner = await _load_owner(db, kb.user_id)
        items.append(_serialize_kb(kb, owner))
    return PaginatedKBList(items=items, total=total, skip=skip, limit=limit)


@router.get("/{kb_id}", response_model=KBResponse)
async def get_kb(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)
    owner = await _load_owner(db, kb.user_id)
    return _serialize_kb(kb, owner)


@router.patch("/{kb_id}", response_model=KBResponse)
async def update_kb(
    kb_id: int,
    req: KBUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.EDITOR)

    if req.name is not None:
        kb.name = req.name
    if req.description is not None:
        kb.description = req.description
    if req.visibility is not None:
        if req.visibility == Visibility.PUBLIC.value and not is_staff(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Use publish request to share to the public catalog. Admin approval required.",
            )
        if is_staff(current_user):
            kb.visibility = Visibility(req.visibility)
            if kb.visibility == Visibility.PUBLIC:
                kb.publish_status = PublishStatus.APPROVED

    await db.flush()
    owner = await _load_owner(db, kb.user_id)
    return _serialize_kb(kb, owner)


@router.post("/{kb_id}/publish-request", response_model=KBResponse)
async def submit_publish_request(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Request admin approval to publish this knowledge base to the public catalog."""
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.OWNER)
    kb = await request_publish(db, kb, current_user)
    return _serialize_kb(kb, current_user)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.OWNER)
    await db.delete(kb)
    await db.flush()
    from app.services.cache_invalidation import invalidate_kb_rag_cache
    await invalidate_kb_rag_cache(kb_id)


@router.post("/{kb_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    kb_id: int,
    req: MemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.OWNER)

    if req.role == MemberRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign owner role via invite.")

    target_user: User | None = None
    if req.user_id is not None:
        user_result = await db.execute(select(User).where(User.id == req.user_id))
        target_user = user_result.scalar_one_or_none()
    elif req.email:
        email = req.email.strip().lower()
        user_result = await db.execute(select(User).where(func.lower(User.email) == email))
        target_user = user_result.scalar_one_or_none()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide user_id or email.",
        )

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    existing = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == target_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member.")

    member = KnowledgeBaseMember(
        knowledge_base_id=kb_id,
        user_id=target_user.id,
        role=MemberRole(req.role),
    )
    db.add(member)
    await db.flush()
    return _serialize_member(member, target_user)


@router.get("/{kb_id}/members", response_model=list[MemberResponse])
async def list_members(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)

    result = await db.execute(
        select(KnowledgeBaseMember, User)
        .join(User, User.id == KnowledgeBaseMember.user_id)
        .where(KnowledgeBaseMember.knowledge_base_id == kb_id)
        .order_by(KnowledgeBaseMember.created_at.asc())
    )
    rows = result.all()
    return [_serialize_member(member, user) for member, user in rows]


@router.delete("/{kb_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    kb_id: int,
    member_user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.OWNER)

    result = await db.execute(
        select(KnowledgeBaseMember).where(
            KnowledgeBaseMember.knowledge_base_id == kb_id,
            KnowledgeBaseMember.user_id == member_user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    if member.role == MemberRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the owner.")

    await db.delete(member)
    await db.flush()
