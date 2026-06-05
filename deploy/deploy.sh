#!/usr/bin/env bash
# KnowFlow AI — Linux 服务器一键 Docker 部署
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PRODUCTION=false
SKIP_TESTS=false
for arg in "$@"; do
  case "$arg" in
    --production) PRODUCTION=true ;;
    --skip-tests) SKIP_TESTS=true ;;
  esac
done

if [[ ! -f .env ]]; then
  echo "ERROR: .env missing. Run: cp .env.example .env && edit secrets"
  exit 1
fi

echo "==> Building images..."
docker compose build backend celery-worker frontend

UP=(up -d postgres redis chromadb backend celery-worker frontend)
if $PRODUCTION; then
  UP+=(--profile production nginx)
fi
echo "==> Starting: ${UP[*]}"
docker compose "${UP[@]}"

echo "==> Waiting for backend..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    curl -s http://localhost:8000/api/health | head -c 200
    echo
    break
  fi
  sleep 2
done

docker compose logs backend 2>&1 | grep -E "Promoted user|already role=admin" | tail -3 || true

if ! $SKIP_TESTS; then
  (cd backend && python scripts/e2e_acceptance.py)
  docker compose exec -T backend pytest tests/ -q --tb=no
fi

echo "==> Done. Frontend http://localhost:3000  API http://localhost:8000"
echo "    Checklist: docs/zh/17-上线前检查清单.md"
