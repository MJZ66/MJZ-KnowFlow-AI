"""Ensure alembic version is stamped on existing databases before upgrade."""

from __future__ import annotations

import os
import subprocess
import sys


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL_SYNC") or os.environ.get("DATABASE_URL", "")
    for old, new in [
        ("postgresql+asyncpg://", "postgresql://"),
        ("postgresql+psycopg2://", "postgresql://"),
    ]:
        url = url.replace(old, new)
    return url


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def main() -> int:
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not available, skipping stamp check")
        return 0

    url = _db_url()
    if not url:
        return 0

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    cur.execute("SELECT to_regclass('public.users')")
    users_exists = cur.fetchone()[0] is not None

    cur.execute("SELECT to_regclass('public.alembic_version')")
    version_table_exists = cur.fetchone()[0] is not None

    has_revision = False
    if version_table_exists:
        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        row = cur.fetchone()
        has_revision = row is not None and bool(row[0])

    conn.close()

    if users_exists and not has_revision:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        has_activity_cols = _column_exists(cur, "users", "last_login_at")
        has_publish_cols = _column_exists(cur, "knowledge_bases", "publish_status")
        conn.close()

        if not has_activity_cols or not has_publish_cols:
            print(
                "Existing schema detected without alembic revision and missing newer columns "
                "— running alembic upgrade head..."
            )
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            return 0

        print("Existing schema detected without alembic revision — stamping head...")
        subprocess.run(["alembic", "stamp", "head"], check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
