#!/usr/bin/env python3
"""Promote a user by email/username and optionally reset password (startup or CLI)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import or_, select

from app.core.config import get_settings
from app.core.database import async_session
from app.core.security import hash_password
from app.models import User, UserRole


async def promote(
    *,
    email: str | None,
    username: str | None,
    password: str | None,
    role: str,
) -> None:
    settings = get_settings()
    email = (email or settings.PROMOTE_USER_EMAIL or "").strip().lower()
    username = (username or settings.PROMOTE_USER_USERNAME or "").strip()
    password = password or settings.PROMOTE_USER_PASSWORD
    role = role or settings.PROMOTE_USER_ROLE or "admin"

    if not email and not username:
        print("No email/username — skipping promote.")
        return

    try:
        target_role = UserRole(role)
    except ValueError:
        print(f"Invalid role: {role}")
        return

    async with async_session() as session:
        user = None
        if email:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
        if user is None and username:
            result = await session.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()

        if user is None:
            if not email or not password:
                print(f"User not found ({email or username}) and password missing — cannot create.")
                return
            user = User(
                email=email,
                username=username or email.split("@")[0],
                hashed_password=hash_password(password),
                role=target_role,
            )
            session.add(user)
            await session.commit()
            print(f"Created {target_role.value} user: {user.email}")
            return

        if user.role == target_role and not password:
            print(
                f"User id={user.id} email={user.email} already role={target_role.value} — no change."
            )
            return

        user.role = target_role
        if password:
            user.hashed_password = hash_password(password)
        if email and user.email != email:
            conflict = await session.execute(select(User).where(User.email == email, User.id != user.id))
            if conflict.scalar_one_or_none():
                print(f"Cannot set email {email}: already used by another account.")
                return
            user.email = email
        if username and user.username != username:
            user.username = username
        await session.commit()
        print(f"Promoted user id={user.id} email={user.email} username={user.username} role={target_role.value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()
    asyncio.run(
        promote(
            email=args.email,
            username=args.username,
            password=args.password,
            role=args.role,
        )
    )


if __name__ == "__main__":
    main()
