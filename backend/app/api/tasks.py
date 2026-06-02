"""
Background task API routes:
- GET /api/tasks          — List user's tasks
- GET /api/tasks/{task_id} — Get task status
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import BackgroundTask, User
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List current user's background tasks, newest first."""
    result = await db.execute(
        select(BackgroundTask)
        .where(BackgroundTask.user_id == current_user.id)
        .order_by(BackgroundTask.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a background task's status and progress."""
    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task
