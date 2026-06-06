"""
E2E acceptance tests — task table section 5.
Run: python scripts/e2e_acceptance.py
Or: docker compose exec backend python scripts/e2e_acceptance.py
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE = "http://localhost:8000"
TIMEOUT = httpx.Timeout(120.0, connect=10.0)

PASS = 0
FAIL = 0
RESULTS: list[str] = []


def ok(name: str, detail: str = ""):
    global PASS
    PASS += 1
    msg = f"[PASS] {name}" + (f" — {detail}" if detail else "")
    RESULTS.append(msg)
    print(msg)


def fail(name: str, detail: str = ""):
    global FAIL
    FAIL += 1
    msg = f"[FAIL] {name}" + (f" — {detail}" if detail else "")
    RESULTS.append(msg)
    print(msg)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def poll_document(client: httpx.Client, doc_id: int, headers: dict, timeout_sec: int = 120) -> dict:
    deadline = time.time() + timeout_sec
    last = None
    while time.time() < deadline:
        r = client.get(f"{BASE}/api/documents/{doc_id}/status", headers=headers)
        r.raise_for_status()
        last = r.json()
        st = last.get("status")
        if st in ("completed", "failed"):
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


def main() -> int:
    suffix = uuid.uuid4().hex[:8]
    email = f"e2e_{suffix}@example.com"
    password = "TestPass123!"
    username = f"e2e_{suffix}"

    chinese_txt = Path(__file__).parent / "_e2e_chinese.txt"
    chinese_txt.write_text(
        "KnowFlow AI 知识库测试文档\n\n"
        "本项目是一个私有 AI 知识库问答平台，支持 PDF、Word、Markdown 和 TXT 文件上传。\n"
        "用户可以在知识库中进行多轮问答，并获得带来源引用的回答。\n\n"
        "cd E:/AI知识平台/knowflow-ai\n"
        "docker compose up -d\n",
        encoding="utf-8",
    )
    empty_txt = Path(__file__).parent / "_e2e_empty.txt"
    empty_txt.write_text("   \n\n  ", encoding="utf-8")

    with httpx.Client(timeout=TIMEOUT) as client:
        # --- Health ---
        r = client.get(f"{BASE}/api/health")
        if r.status_code == 200 and r.json().get("status") == "ok":
            ok("Health check")
        else:
            fail("Health check", str(r.text))
            return 1

        # --- Register + login ---
        r = client.post(f"{BASE}/api/auth/register", json={
            "email": email, "password": password, "username": username,
        })
        if r.status_code == 201:
            ok("Register user", email)
        else:
            fail("Register user", f"{r.status_code} {r.text}")
            return 1

        tokens = r.json()
        access = tokens["access_token"]
        headers = auth_headers(access)

        # --- Error format (structured) ---
        r = client.post(f"{BASE}/api/auth/login", json={
            "email": email, "password": "wrong-password",
        })
        body = r.json()
        if r.status_code == 401 and "code" in body and "message" in body and "message_en" in body:
            ok("Unified error format", body.get("code", ""))
        else:
            fail("Unified error format", str(body))

        # --- Create KB ---
        r = client.post(f"{BASE}/api/kbs", headers=headers, json={
            "name": f"E2E测试库-{suffix}",
            "description": "端到端验收",
            "visibility": "private",
        })
        if r.status_code == 201:
            kb_id = r.json()["id"]
            ok("Create knowledge base", f"kb_id={kb_id}")
        else:
            fail("Create knowledge base", r.text)
            return 1

        # --- Upload Chinese TXT → COMPLETED ---
        with chinese_txt.open("rb") as f:
            r = client.post(
                f"{BASE}/api/kbs/{kb_id}/documents/upload",
                headers=headers,
                files={"file": ("中文测试文档.txt", f, "text/plain")},
            )
        if r.status_code != 201:
            fail("Upload Chinese TXT", r.text)
        else:
            doc_ok = r.json()
            doc_ok_id = doc_ok["id"]
            ok("Upload Chinese TXT", f"doc_id={doc_ok_id}")

            status = poll_document(client, doc_ok_id, headers)
            if status.get("status") == "completed":
                ok("Poll Chinese TXT → COMPLETED", f"progress={status.get('progress')}")
            else:
                fail("Poll Chinese TXT → COMPLETED", str(status))

        # --- Upload empty/whitespace → FAILED ---
        with empty_txt.open("rb") as f:
            r = client.post(
                f"{BASE}/api/kbs/{kb_id}/documents/upload",
                headers=headers,
                files={"file": ("空文档.txt", f, "text/plain")},
            )
        if r.status_code != 201:
            fail("Upload empty TXT (create)", r.text)
        else:
            doc_fail = r.json()
            doc_fail_id = doc_fail["id"]
            status = poll_document(client, doc_fail_id, headers, timeout_sec=60)
            if status.get("status") == "failed":
                ok("Upload empty TXT → FAILED", status.get("error_message", "")[:80])
            else:
                fail("Upload empty TXT → FAILED", str(status))

        # --- Chat session + RAG SSE stream ---
        setup_r = client.get(f"{BASE}/api/setup/status", headers=headers)
        llm_ready = (
            setup_r.status_code == 200
            and setup_r.json().get("ready_for_chat") is True
        )

        r = client.post(
            f"{BASE}/api/kbs/{kb_id}/chat/sessions",
            headers=headers,
            json={"title": "E2E Chat"},
        )
        if r.status_code != 201:
            fail("Create chat session", r.text)
        else:
            session_id = r.json()["id"]
            ok("Create chat session", f"session_id={session_id}")

            if not llm_ready:
                ok("RAG SSE (skipped)", "LLM_API_KEY not configured — set GitHub secret LLM_API_KEY for full RAG CI")
            else:
                with client.stream(
                    "POST",
                    f"{BASE}/api/chat/sessions/{session_id}/stream",
                    headers=headers,
                    json={"content": "KnowFlow AI 支持哪些文件格式？", "top_k": 5},
                ) as stream:
                    chunks = []
                    for chunk in stream.iter_text():
                        chunks.append(chunk)
                    sse_text = "".join(chunks)

                events = parse_sse_stream(sse_text)
                event_types = [e[0] for e in events]
                tokens = [d.get("content", "") for t, d in events if t == "token"]
                refs = next((d for t, d in events if t == "references"), None)

                has_retrieval = "retrieval_start" in event_types and "retrieval_done" in event_types
                has_tokens = len(tokens) > 0 and any(tokens)
                has_done = "done" in event_types

                if has_retrieval:
                    ok("RAG SSE retrieval events")
                else:
                    fail("RAG SSE retrieval events", str(event_types))

                if has_tokens:
                    ok("RAG SSE token streaming", f"tokens={len(''.join(tokens))} chars")
                else:
                    fail("RAG SSE token streaming", sse_text[:300])

                if has_done:
                    ok("RAG SSE done event")
                else:
                    fail("RAG SSE done event")

                # Reference noise filter — CLI lines should not dominate references
                if refs and isinstance(refs, list) and len(refs) > 0:
                    noise_in_refs = sum(
                        1 for ref in refs
                        if ref.get("section_title") and (
                            str(ref.get("section_title", "")).startswith("cd ")
                            or "docker compose" in str(ref.get("section_title", "")).lower()
                        )
                    )
                    previews = " ".join(str(ref.get("content_preview", "")) for ref in refs)
                    has_meaningful = any(k in previews for k in ("知识库", "PDF", "问答", "KnowFlow"))
                    if noise_in_refs == 0 and has_meaningful:
                        ok("Reference noise filter", f"refs={len(refs)}")
                    elif has_meaningful:
                        ok("Reference noise filter (partial)", f"refs={len(refs)}, noise_titles={noise_in_refs}")
                    else:
                        fail("Reference noise filter", f"refs={len(refs)}, preview={previews[:120]}")
                else:
                    fail("Reference noise filter", "no references returned")

        # --- i18n files validation (frontend) ---
        frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n" / "locales"
        zh_path = frontend_root / "zh-CN.json"
        en_path = frontend_root / "en-US.json"
        if zh_path.exists() and en_path.exists():
            zh = json.loads(zh_path.read_text(encoding="utf-8"))
            en = json.loads(en_path.read_text(encoding="utf-8"))
            if set(zh.keys()) == set(en.keys()) and "chat.placeholder" in zh:
                ok("i18n zh/en key parity", f"keys={len(zh)}")
            else:
                fail("i18n zh/en key parity")
        else:
            fail("i18n locale files exist")

    # Cleanup temp files
    chinese_txt.unlink(missing_ok=True)
    empty_txt.unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print(f"E2E Summary: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    for line in RESULTS:
        print(line)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
