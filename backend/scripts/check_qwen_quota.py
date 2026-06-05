#!/usr/bin/env python3
"""
Check Qwen (DashScope) API key validity and estimate project token budget.

DashScope does NOT expose a stable public API for remaining free quota.
Run this script, then confirm exact balance in 百炼控制台:
  https://bailian.console.aliyun.com/
  -> 模型广场 -> qwen-plus -> 免费额度

Usage:
  python scripts/check_qwen_quota.py
  docker compose exec backend python scripts/check_qwen_quota.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings

# Rough tokens per RAG turn for KnowFlow (qwen-plus, top_k=5, history<=10 rounds)
EST_INPUT_PER_CHAT = 6_000
EST_OUTPUT_PER_CHAT = 500


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def main() -> int:
    settings = get_settings()
    key = settings.LLM_API_KEY.strip()
    base = settings.LLM_API_BASE.rstrip("/")
    model = settings.LLM_MODEL

    print("=" * 60)
    print("KnowFlow — Qwen / DashScope 状态检查")
    print("=" * 60)
    print(f"LLM_PROVIDER : {settings.LLM_PROVIDER}")
    print(f"LLM_MODEL    : {model}")
    print(f"EMBEDDING    : {settings.EMBEDDING_PROVIDER} (不消耗千问 Token)")
    print(f"API_BASE     : {base}")
    print(f"API_KEY      : {'已配置 ' + mask_key(key) if key and 'your_' not in key else '未配置或为占位符'}")

    if not key or "your_" in key:
        print("\n请在 .env 中设置 LLM_API_KEY 后重试。")
        return 1

    with httpx.Client(timeout=60.0) as client:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        r = client.post(
            f"{base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "回复 OK"}],
                "max_tokens": 5,
            },
        )

    print(f"\n探测请求 HTTP 状态: {r.status_code}")

    if r.status_code == 200:
        data = r.json()
        usage = data.get("usage") or {}
        print("API 可用 ✓")
        print(f"本次探测消耗: {json.dumps(usage, ensure_ascii=False)}")
    elif r.status_code == 403:
        body = r.text[:500]
        print("API 返回 403 — 常见原因：免费额度用尽且未开通按量付费")
        print(body)
        if "FreeTierOnly" in body or "free" in body.lower():
            print("\n建议：百炼控制台关闭「仅使用免费额度」或充值后开启按量付费。")
        return 2
    elif r.status_code == 401:
        print("API Key 无效或已失效，请在百炼控制台重新创建 Key。")
        return 3
    else:
        print(r.text[:500])
        return 4

    print("\n--- 剩余额度说明 ---")
    print("阿里云百炼不提供稳定的「剩余 Token」开放 API。")
    print("精确余额请到控制台查看（约 1 小时延迟）：")
    print("  百炼控制台 -> 模型广场 -> 选择 qwen-plus -> 免费额度")
    print("  或：费用与成本 -> 账单详情（产品：大模型服务平台百炼）")

    print("\n--- 本项目单次问答 Token 估算（qwen-plus RAG）---")
    print(f"  输入约 {EST_INPUT_PER_CHAT:,}（检索片段 + 历史 + 提示词）")
    print(f"  输出约 {EST_OUTPUT_PER_CHAT:,}")
    per_turn = EST_INPUT_PER_CHAT + EST_OUTPUT_PER_CHAT
    print(f"  合计约 {per_turn:,} Token / 次问答")

    for total_label, total in [("100 万免费额度", 1_000_000), ("50 万", 500_000), ("10 万", 100_000)]:
        chats = total // per_turn
        print(f"  若剩余 {total_label}，约可支撑 {chats:,} 次 RAG 问答")

    print("\n仅 LLM 问答消耗千问 Token；文档向量化当前为 hash，不走千问 API。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
