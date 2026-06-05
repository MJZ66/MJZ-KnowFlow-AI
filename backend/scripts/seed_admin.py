#!/usr/bin/env python3
"""Create or update the default admin account from environment variables."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session
from app.core.security import hash_password
from app.models import User, UserRole


async def seed_admin() -> None:
    settings = get_settings()
    if not settings.SEED_ADMIN_ON_START:
        print("SEED_ADMIN_ON_START=false — skipping admin seed.")
        return

    email = settings.ADMIN_EMAIL.strip().lower()
    if not email or not settings.ADMIN_PASSWORD:
        print("ADMIN_EMAIL or ADMIN_PASSWORD empty — skipping admin seed.")
        return

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                username=settings.ADMIN_USERNAME or "knowflow_admin",
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
            session.add(user)
            await session.commit()
            print(f"Created admin user: {email}")
            return

        changed = False
        if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            user.role = UserRole.ADMIN
            changed = True
        if settings.SEED_ADMIN_UPDATE_PASSWORD:
            user.hashed_password = hash_password(settings.ADMIN_PASSWORD)
            changed = True
        if changed:
            await session.commit()
            print(f"Updated admin user: {email}")
        else:
            print(f"Admin user already exists: {email}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
