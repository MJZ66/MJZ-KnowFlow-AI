"""System setup status — safe to expose (no secret values)."""

from __future__ import annotations

from app.core.config import Settings, get_settings

_PLACEHOLDER_FRAGMENTS = (
    "your_",
    "change-me",
    "replace-with",
    "xxx",
    "placeholder",
)


def is_secret_configured(value: str) -> bool:
    """True when env value looks like a real secret, not a template placeholder."""
    if not value or not value.strip():
        return False
    low = value.strip().lower()
    if len(low) < 8:
        return False
    return not any(frag in low for frag in _PLACEHOLDER_FRAGMENTS)


def build_setup_status(settings: Settings | None = None) -> dict:
    s = settings or get_settings()

    llm_ok = is_secret_configured(s.LLM_API_KEY)
    deepseek_ok = is_secret_configured(s.DEEPSEEK_API_KEY)

    return {
        "llm": {
            "provider": s.LLM_PROVIDER,
            "model": s.LLM_MODEL,
            "configured": llm_ok,
            "api_base": s.LLM_API_BASE,
        },
        "deepseek": {
            "configured": deepseek_ok,
            "api_base": s.DEEPSEEK_API_BASE,
            "usage_hint": "VECTOR_PROVIDER=deepseek or LLM openai_compatible + DeepSeek base",
        },
        "embedding": {
            "provider": s.EMBEDDING_PROVIDER,
            "vector_provider": s.VECTOR_PROVIDER,
            "dim": s.EMBEDDING_DIM,
        },
        "task_backend": s.TASK_BACKEND,
        "ocr": {
            "enabled": s.OCR_ENABLED,
            "languages": s.OCR_LANGUAGES,
        },
        "metrics_enabled": s.METRICS_ENABLED,
        "ready_for_chat": llm_ok,
        "issues": _collect_issues(s, llm_ok),
    }


def _collect_issues(s: Settings, llm_ok: bool) -> list[dict]:
    issues: list[dict] = []
    if not llm_ok:
        issues.append({
            "code": "llm_key_missing",
            "severity": "error",
            "message_zh": "未配置 LLM API Key，问答功能不可用",
            "message_en": "LLM API key is not configured — chat will not work",
        })
    if s.APP_ENV == "production" and s.SECRET_KEY.startswith("change-me"):
        issues.append({
            "code": "secret_key_weak",
            "severity": "error",
            "message_zh": "生产环境 SECRET_KEY 不安全",
            "message_en": "SECRET_KEY is insecure for production",
        })
    if s.TASK_BACKEND == "celery" and s.APP_ENV == "production":
        issues.append({
            "code": "celery_required",
            "severity": "info",
            "message_zh": "文档处理依赖 Celery Worker 运行",
            "message_en": "Document processing requires a running Celery worker",
        })
    if s.OCR_ENABLED:
        try:
            from app.services.ocr_service import ocr_available

            if not ocr_available():
                issues.append({
                    "code": "ocr_unavailable",
                    "severity": "warning",
                    "message_zh": "OCR 已启用但 Tesseract 未安装或不可用",
                    "message_en": "OCR is enabled but Tesseract is not available",
                })
        except ImportError:
            issues.append({
                "code": "ocr_deps_missing",
                "severity": "warning",
                "message_zh": "OCR 依赖未安装",
                "message_en": "OCR dependencies are not installed",
            })
    return issues
