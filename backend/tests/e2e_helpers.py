"""Shared E2E test helpers — used by pytest and scripts/e2e_acceptance.py."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import httpx

BASE = os.environ.get("KNOWFLOW_API_BASE", "http://localhost:8000")
TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def poll_document(client: httpx.Client, doc_id: int, headers: dict, timeout_sec: int = 120) -> dict:
    deadline = time.time() + timeout_sec
    last = None
    while time.time() < deadline:
        r = client.get(f"{BASE}/api/documents/{doc_id}/status", headers=headers)
        r.raise_for_status()
        last = r.json()
        if last.get("status") in ("completed", "failed"):
            return last
        time.sleep(2)
    return last or {}


def parse_sse_stream(text: str) -> list[tuple[str, dict]]:
    events = []
    event_type = ""
    for line in text.split("\n"):
        if line.startswith("event: "):
            event_type = line[7:].strip()
        elif line.startswith("data: "):
            try:
                events.append((event_type, json.loads(line[6:])))
            except json.JSONDecodeError:
                pass
    return events


def unique_user():
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"e2e_{suffix}@example.com",
        "password": "TestPass123!",
        "username": f"e2e_{suffix}",
    }


def make_chinese_txt(path: Path) -> None:
    path.write_text(
        "KnowFlow AI 知识库测试文档\n\n"
        "本项目是一个私有 AI 知识库问答平台，支持 PDF、Word、Markdown 和 TXT 文件上传。\n"
        "技术栈包括 PostgreSQL、Redis 和 ChromaDB。\n"
        "用户可以在知识库中进行多轮问答，并获得带来源引用的回答。\n\n"
        "cd E:/AI知识平台/knowflow-ai\n"
        "docker compose up -d\n",
        encoding="utf-8",
    )
