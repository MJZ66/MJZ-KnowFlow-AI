#!/bin/sh
set -e

echo "KnowFlow AI entrypoint — APP_ENV=${APP_ENV:-development}"

# Wait for PostgreSQL
if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for PostgreSQL..."
  for i in $(seq 1 30); do
    if python -c "
import os, sys
try:
    import psycopg2
    url = os.environ.get('DATABASE_URL_SYNC') or os.environ.get('DATABASE_URL', '')
    for old, new in [
        ('postgresql+asyncpg://', 'postgresql://'),
        ('postgresql+psycopg2://', 'postgresql://'),
    ]:
        url = url.replace(old, new)
    conn = psycopg2.connect(url)
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
      echo "PostgreSQL is ready."
      break
    fi
    echo "  attempt $i/30..."
    sleep 2
  done
fi

if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
  echo "Running database migrations..."
  python scripts/ensure_migrations.py
  alembic upgrade head
fi

if [ "${SEED_ADMIN_ON_START:-true}" = "true" ]; then
  echo "Seeding default admin account (if configured)..."
  python scripts/seed_admin.py || echo "Admin seed skipped or failed (non-fatal)."
fi

if [ "${PROMOTE_USER_ON_START:-false}" = "true" ]; then
  echo "Promoting configured user account..."
  python scripts/promote_account.py || echo "User promote skipped or failed (non-fatal)."
fi

if [ "$#" -gt 0 ]; then
  echo "Running custom command: $*"
  exec "$@"
fi

if [ "${APP_ENV:-development}" = "production" ]; then
  echo "Starting uvicorn (production, 4 workers)..."
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
else
  echo "Starting uvicorn (development, reload)..."
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
