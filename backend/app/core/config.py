"""
Application configuration loaded from environment variables.
All settings must be configured via .env — no hardcoded secrets.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    # ============================================
    # Application
    # ============================================
    APP_NAME: str = "KnowFlow AI"
    APP_ENV: Literal["development", "production"] = "development"
    DEBUG: bool = False
    RUN_MIGRATIONS_ON_START: bool = True

    # ============================================
    # Security
    # ============================================
    SECRET_KEY: str = "change-me-to-a-random-secret-key-at-least-32-chars"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ============================================
    # Database
    # ============================================
    DATABASE_URL: str = "postgresql+asyncpg://knowflow:knowflow_secret@localhost:5432/knowflow"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://knowflow:knowflow_secret@localhost:5432/knowflow"

    # ============================================
    # Redis
    # ============================================
    REDIS_URL: str = "redis://localhost:6379/0"

    # Task queue
    TASK_BACKEND: Literal["background", "celery"] = "background"

    # RAG query cache (Redis)
    RAG_CACHE_ENABLED: bool = False
    RAG_CACHE_TTL_SECONDS: int = 300

    # ============================================
    # ChromaDB
    # ============================================
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # ============================================
    # LLM Provider
    # ============================================
    LLM_PROVIDER: Literal["qwen", "openai_compatible", "ollama"] = "qwen"
    LLM_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen-plus"
    LLM_STREAM: bool = True

    # ============================================
    # Vector / Embedding
    # ============================================
    VECTOR_PROVIDER: Literal["deepseek", "chroma", "chroma_hash"] = "chroma_hash"
    EMBEDDING_PROVIDER: Literal["hash", "local_bge", "dashscope", "openai_compatible"] = "hash"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 384
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_API_BASE: str = ""
    EMBEDDING_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_VECTOR_INDEX_PREFIX: str = "kb_"

    # ============================================
    # Reranker
    # ============================================
    RERANKER_ENABLED: bool = False
    RERANKER_PROVIDER: Literal["none", "noop", "local_bge"] = "none"
    RERANKER_MODEL: str = "bge-reranker-v2-m3"
    RERANKER_TOP_N: int = 5
    RETRIEVAL_OVERSAMPLE: int = 4

    # ============================================
    # Hybrid Search
    # ============================================
    HYBRID_SEARCH_ENABLED: bool = False
    HYBRID_VECTOR_WEIGHT: float = 0.7
    HYBRID_KEYWORD_WEIGHT: float = 0.3
    KEYWORD_TOP_K: int = 20
    VECTOR_TOP_K: int = 20

    # ============================================
    # File Upload
    # ============================================
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 30
    MAX_UPLOAD_SIZE_MB: int = 30
    ALLOWED_FILE_TYPES: list[str] = [
        "pdf", "docx", "md", "txt", "xlsx", "xls",
        "png", "jpg", "jpeg", "webp", "gif", "bmp",
    ]
    ALLOWED_FILE_EXTENSIONS: str = "pdf,docx,md,txt,xlsx,xls,png,jpg,jpeg,webp,gif,bmp"
    MAX_FILENAME_LENGTH: int = 150

    # ============================================
    # Limits
    # ============================================
    MAX_DOCS_PER_KB: int = 100
    MAX_KBS_PER_USER: int = 10

    # ============================================
    # RAG
    # ============================================
    TOP_K_RETRIEVAL: int = 5
    MAX_CHAT_HISTORY_ROUNDS: int = 10
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # ============================================
    # Database pool
    # ============================================
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # ============================================
    # Celery worker
    # ============================================
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_TIME_LIMIT: int = 600

    # ============================================
    # OCR (image documents)
    # ============================================
    OCR_ENABLED: bool = True
    OCR_LANGUAGES: str = "chi_sim+eng"

    # ============================================
    # Observability
    # ============================================
    METRICS_ENABLED: bool = True

    # ============================================
    # Admin bootstrap & presence
    # ============================================
    SEED_ADMIN_ON_START: bool = True
    ADMIN_EMAIL: str = "admin@knowflow.local"
    ADMIN_USERNAME: str = "knowflow_admin"
    ADMIN_PASSWORD: str = "Admin@KnowFlow2026"
    SEED_ADMIN_UPDATE_PASSWORD: bool = False
    USER_ONLINE_THRESHOLD_MINUTES: int = 5

    PROMOTE_USER_ON_START: bool = True
    PROMOTE_USER_EMAIL: str = ""
    PROMOTE_USER_USERNAME: str = ""
    PROMOTE_USER_PASSWORD: str = ""
    PROMOTE_USER_ROLE: str = "admin"

    model_config = dict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def ALLOWED_ORIGINS_LIST(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def ALLOWED_EXTENSIONS_SET(self) -> set[str]:
        if self.ALLOWED_FILE_EXTENSIONS:
            return {e.strip().lower() for e in self.ALLOWED_FILE_EXTENSIONS.split(",") if e.strip()}
        return {t.lower() for t in self.ALLOWED_FILE_TYPES}

    @property
    def max_upload_bytes(self) -> int:
        limit = self.MAX_UPLOAD_SIZE_MB or self.MAX_FILE_SIZE_MB
        return limit * 1024 * 1024


DEFAULT_SECRET_KEY = "change-me-to-a-random-secret-key-at-least-32-chars"


def validate_production_settings(settings: Settings | None = None) -> None:
    """Fail fast when production uses insecure defaults."""
    import logging

    s = settings or get_settings()
    log = logging.getLogger(__name__)

    insecure = (
        not s.SECRET_KEY
        or s.SECRET_KEY == DEFAULT_SECRET_KEY
        or len(s.SECRET_KEY) < 32
    )
    if s.APP_ENV == "production" and insecure:
        raise RuntimeError("SECRET_KEY is insecure for production.")
    if s.APP_ENV != "production" and insecure:
        log.warning("SECRET_KEY is using the default value — acceptable in development only.")

    if s.APP_ENV == "production" and s.EMBEDDING_PROVIDER == "hash":
        log.warning(
            "EMBEDDING_PROVIDER=hash in production — retrieval quality is limited. "
            "Set EMBEDDING_PROVIDER=local_bge, VECTOR_PROVIDER=chroma, EMBEDDING_DIM=1024."
        )

    if s.APP_ENV == "production" and s.EMBEDDING_PROVIDER == "local_bge":
        if s.VECTOR_PROVIDER == "chroma_hash":
            raise RuntimeError(
                "Production local_bge requires VECTOR_PROVIDER=chroma (not chroma_hash)."
            )
        if s.EMBEDDING_DIM != 1024:
            log.warning(
                "BAAI/bge-m3 uses 1024 dimensions; EMBEDDING_DIM=%s may cause mismatch.",
                s.EMBEDDING_DIM,
            )


def validate_embedding_runtime(settings: Settings | None = None) -> None:
    """Ensure configured embedding provider is actually available at startup."""
    from app.services.embedding_service import EmbeddingServiceFactory

    s = settings or get_settings()
    if s.EMBEDDING_PROVIDER != "local_bge":
        return

    svc = EmbeddingServiceFactory.get_service()
    if svc.provider_name != "local_bge":
        msg = (
            f"EMBEDDING_PROVIDER=local_bge but runtime provider is {svc.provider_name}. "
            "Install sentence-transformers and ensure the model can load."
        )
        if s.APP_ENV == "production":
            raise RuntimeError(msg)
        import logging
        logging.getLogger(__name__).warning(msg)

@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
