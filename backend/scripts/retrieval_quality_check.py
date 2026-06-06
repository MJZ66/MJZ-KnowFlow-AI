"""
Retrieval quality acceptance script — Phase 2-3 validation.

Run:
  python scripts/retrieval_quality_check.py
  docker compose exec backend python scripts/retrieval_quality_check.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE = os.environ.get("KNOWFLOW_API_BASE", "http://localhost:8000")
TIMEOUT = httpx.Timeout(120.0, connect=10.0)

STANDARD_DOC = """KnowFlow AI 的后端使用 FastAPI。
数据库使用 PostgreSQL。
缓存系统使用 Redis。
向量数据库使用 ChromaDB。
系统支持文档上传、文本切片、向量检索和 RAG 问答。
"""

TEST_QUERIES = [
    ("KnowFlow AI 的后端使用了哪些组件？", ["FastAPI", "PostgreSQL", "Redis", "ChromaDB"]),
    ("数据库使用什么？", ["PostgreSQL"]),
    ("缓存系统是什么？", ["Redis"]),
    ("向量数据库是什么？", ["ChromaDB"]),
    ("系统是否支持 RAG 问答？", ["RAG"]),
]

NOISE_MARKERS = ("docker compose", "cd E:", "powershell", "npm run")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def poll_document(client: httpx.Client, doc_id: int, headers: dict, timeout_sec: int = 120) -> dict:
    deadline = time.time() + timeout_sec
    last: dict = {}
    while time.time() < deadline:
        r = client.get(f"{BASE}/api/documents/{doc_id}/status", headers=headers)
        r.raise_for_status()
        last = r.json()
        if last.get("status") in ("completed", "failed"):
            return last
        time.sleep(2)
    return last


def print_stats(stats: dict) -> None:
    print(f"[QUERY] {stats['query']}")
    print(f"mode={stats['mode']}")
    print(f"raw_count={stats['raw_count']}")
    print(f"valid_count={stats['valid_count']}")
    print(f"reranked_count={stats['reranked_count']}")
    print()
    for i, ref in enumerate(stats.get("references") or [], start=1):
        score = ref.get("score", "-")
        filename = ref.get("source_filename", "unknown")
        preview = (ref.get("content_preview") or "").replace("\n", " ")[:120]
        print(f"#{i} score={score} file={filename}")
        print(f"preview={preview}")
    print("-" * 60)


async def run_retrieval_checks(kb_id: int, headers: dict) -> list[dict]:
    from app.core.database import async_session
    from app.rag.rag_service import RAGService

    rag = RAGService()
    results: list[dict] = []

    async with async_session() as db:
        for query, _expected in TEST_QUERIES:
            stats = await rag.retrieve_with_stats(db, kb_id, query, top_k=5)
            results.append(stats)
            print_stats(stats)

    return results


def validate_results(results: list[dict]) -> tuple[int, int]:
    passed = 0
    failed = 0

    for stats, (_query, expected_terms) in zip(results, TEST_QUERIES):
        previews = " ".join(
            str(r.get("content_preview", "")) for r in stats.get("references") or []
        )
        query_ok = all(term in previews for term in expected_terms)
        if not query_ok:
            print(f"[FAIL] keyword recall missing for: {stats['query']} expected={expected_terms}")
            failed += 1
            continue

        # dedupe check
        keys = [
            f"{r.get('document_id')}_{r.get('chunk_index')}"
            for r in stats.get("references") or []
        ]
        if len(keys) != len(set(keys)):
            print(f"[FAIL] duplicate references for: {stats['query']}")
            failed += 1
            continue

        if any(marker.lower() in previews.lower() for marker in NOISE_MARKERS):
            print(f"[FAIL] command noise in references for: {stats['query']}")
            failed += 1
            continue

        print(f"[PASS] {stats['query']}")
        passed += 1

    return passed, failed


def setup_kb_and_doc(client: httpx.Client) -> tuple[dict, int]:
    suffix = uuid.uuid4().hex[:8]
    user = {
        "email": f"rq_{suffix}@example.com",
        "password": "TestPass123!",
        "username": f"rq_{suffix}",
    }
    r = client.post(f"{BASE}/api/auth/register", json=user)
    r.raise_for_status()
    headers: dict = {}

    kb = client.post(
        f"{BASE}/api/kbs",
        json={"name": f"Retrieval QA {suffix}", "description": "quality check", "visibility": "private"},
    ).json()

    doc_path = Path(__file__).parent / "_retrieval_quality.txt"
    doc_path.write_text(STANDARD_DOC, encoding="utf-8")
    with doc_path.open("rb") as f:
        doc = client.post(
            f"/api/kbs/{kb['id']}/documents/upload",
            files={"file": ("中文测试文档.txt", f, "text/plain")},
        )
    doc.raise_for_status()
    doc_id = doc.json()["id"]

    status = poll_document(client, doc_id, headers)
    if status.get("status") != "completed":
        raise RuntimeError(f"Document not completed: {status}")

    return headers, kb["id"]


def main() -> int:
    from app.core.config import get_settings

    settings = get_settings()
    print("=" * 60)
    print("KnowFlow AI — Retrieval Quality Check")
    print(f"API: {BASE}")
    print(f"HYBRID_SEARCH_ENABLED={settings.HYBRID_SEARCH_ENABLED}")
    print(f"RERANKER_ENABLED={settings.RERANKER_ENABLED}")
    print(f"EMBEDDING_PROVIDER={settings.EMBEDDING_PROVIDER}")
    print(f"VECTOR_PROVIDER={settings.VECTOR_PROVIDER}")
    print("=" * 60)

    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        install_csrf_hook(client)
        health = client.get("/api/health")
        health.raise_for_status()
        headers, kb_id = setup_kb_and_doc(client)

    results = asyncio.run(run_retrieval_checks(kb_id, headers))
    passed, failed = validate_results(results)

    print("=" * 60)
    print(f"Summary: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.e2e_helpers import install_csrf_hook
    raise SystemExit(main())
