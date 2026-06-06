"""Setup / configuration status for onboarding UI."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.health import readiness_report
from app.models import User
from app.services.setup_status import build_setup_status

router = APIRouter(tags=["Setup"])


@router.get("/api/setup/status")
async def get_setup_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return configuration and dependency status (no secrets)."""
    _ = db  # reserved for future per-user checks
    _ = current_user
    setup = build_setup_status()
    readiness = await readiness_report()
    return {
        **setup,
        "readiness": readiness,
        "overall_ok": setup["ready_for_chat"] and readiness.get("status") == "ok",
    }
