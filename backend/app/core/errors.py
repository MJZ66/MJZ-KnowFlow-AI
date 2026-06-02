"""
Standardized error codes and messages for KnowFlow AI API.

Usage:
    from app.core.errors import ErrorCode, AppError
    raise AppError(ErrorCode.KB_NOT_FOUND)
"""

from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    # Auth
    AUTH_NOT_AUTHENTICATED = "AUTH_NOT_AUTHENTICATED"
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_EMAIL_EXISTS = "AUTH_EMAIL_EXISTS"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"

    # Permission
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ADMIN_REQUIRED = "ADMIN_REQUIRED"

    # Knowledge Base
    KB_NOT_FOUND = "KB_NOT_FOUND"
    KB_LIMIT_REACHED = "KB_LIMIT_REACHED"

    # Document
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_LIMIT_REACHED = "DOCUMENT_LIMIT_REACHED"
    DOCUMENT_INVALID_TYPE = "DOCUMENT_INVALID_TYPE"
    DOCUMENT_TOO_LARGE = "DOCUMENT_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    DOCUMENT_PROCESS_FAILED = "DOCUMENT_PROCESS_FAILED"
    DOCUMENT_EMPTY_CONTENT = "DOCUMENT_EMPTY_CONTENT"

    # Vector / Search
    VECTOR_SEARCH_FAILED = "VECTOR_SEARCH_FAILED"
    VECTOR_DIMENSION_MISMATCH = "VECTOR_DIMENSION_MISMATCH"

    # LLM
    LLM_GENERATION_FAILED = "LLM_GENERATION_FAILED"

    # Chat
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    MEMBER_ALREADY_EXISTS = "MEMBER_ALREADY_EXISTS"
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"

    # General
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Chinese messages for each error code
ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.AUTH_NOT_AUTHENTICATED: "未登录或登录已过期",
    ErrorCode.AUTH_INVALID_TOKEN: "登录凭证无效",
    ErrorCode.AUTH_EMAIL_EXISTS: "该邮箱已注册",
    ErrorCode.AUTH_INVALID_CREDENTIALS: "邮箱或密码错误",
    ErrorCode.PERMISSION_DENIED: "无权限访问",
    ErrorCode.ADMIN_REQUIRED: "需要管理员权限",
    ErrorCode.KB_NOT_FOUND: "知识库不存在",
    ErrorCode.KB_LIMIT_REACHED: "已达到知识库数量上限",
    ErrorCode.DOCUMENT_NOT_FOUND: "文档不存在",
    ErrorCode.DOCUMENT_LIMIT_REACHED: "已达到文档数量上限",
    ErrorCode.DOCUMENT_INVALID_TYPE: "不支持的文件类型",
    ErrorCode.DOCUMENT_TOO_LARGE: "文件过大",
    ErrorCode.UNSUPPORTED_FILE_TYPE: "不支持的文件类型",
    ErrorCode.FILE_TOO_LARGE: "文件大小超过限制",
    ErrorCode.DOCUMENT_PROCESS_FAILED: "文档处理失败",
    ErrorCode.DOCUMENT_EMPTY_CONTENT: "文档内容为空",
    ErrorCode.VECTOR_SEARCH_FAILED: "向量检索失败",
    ErrorCode.VECTOR_DIMENSION_MISMATCH: "向量维度不一致，请为新的向量模型创建新知识库或重建索引",
    ErrorCode.LLM_GENERATION_FAILED: "回答生成失败",
    ErrorCode.SESSION_NOT_FOUND: "会话不存在",
    ErrorCode.MEMBER_ALREADY_EXISTS: "该用户已是成员",
    ErrorCode.MEMBER_NOT_FOUND: "成员不存在",
    ErrorCode.VALIDATION_ERROR: "请求参数错误",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
}

# English messages
ERROR_MESSAGES_EN: dict[ErrorCode, str] = {
    ErrorCode.AUTH_NOT_AUTHENTICATED: "Not authenticated",
    ErrorCode.AUTH_INVALID_TOKEN: "Invalid token",
    ErrorCode.AUTH_EMAIL_EXISTS: "Email already registered",
    ErrorCode.AUTH_INVALID_CREDENTIALS: "Invalid email or password",
    ErrorCode.PERMISSION_DENIED: "Permission denied",
    ErrorCode.ADMIN_REQUIRED: "Admin privileges required",
    ErrorCode.KB_NOT_FOUND: "Knowledge base not found",
    ErrorCode.KB_LIMIT_REACHED: "Knowledge base limit reached",
    ErrorCode.DOCUMENT_NOT_FOUND: "Document not found",
    ErrorCode.DOCUMENT_LIMIT_REACHED: "Document limit reached",
    ErrorCode.DOCUMENT_INVALID_TYPE: "Unsupported file type",
    ErrorCode.DOCUMENT_TOO_LARGE: "File too large",
    ErrorCode.UNSUPPORTED_FILE_TYPE: "Unsupported file type",
    ErrorCode.FILE_TOO_LARGE: "File size exceeds the limit",
    ErrorCode.DOCUMENT_PROCESS_FAILED: "Document processing failed",
    ErrorCode.DOCUMENT_EMPTY_CONTENT: "Document has no content",
    ErrorCode.VECTOR_SEARCH_FAILED: "Vector search failed",
    ErrorCode.VECTOR_DIMENSION_MISMATCH: "Vector dimension mismatch. Please create a new knowledge base or rebuild the index.",
    ErrorCode.LLM_GENERATION_FAILED: "Answer generation failed",
    ErrorCode.SESSION_NOT_FOUND: "Session not found",
    ErrorCode.MEMBER_ALREADY_EXISTS: "User is already a member",
    ErrorCode.MEMBER_NOT_FOUND: "Member not found",
    ErrorCode.VALIDATION_ERROR: "Validation error",
    ErrorCode.INTERNAL_ERROR: "Internal server error",
}


class AppError(Exception):
    """Application-level error with standard code and message."""

    def __init__(self, code: ErrorCode, detail: Optional[str] = None):
        self.code = code
        self.detail = detail or ERROR_MESSAGES.get(code, str(code))
        super().__init__(self.detail)


def error_response(code: ErrorCode, detail: Optional[str] = None) -> dict:
    """Build a standardized error response dict."""
    zh = ERROR_MESSAGES.get(code, detail or "")
    en = ERROR_MESSAGES_EN.get(code, detail or "")
    if detail and detail not in (zh, en):
        en = detail
    return {
        "code": code.value,
        "message": zh,
        "message_en": en,
    }


# Map legacy HTTPException detail strings to ErrorCode
_DETAIL_TO_CODE: dict[str, ErrorCode] = {
    "Email already registered.": ErrorCode.AUTH_EMAIL_EXISTS,
    "Invalid email or password.": ErrorCode.AUTH_INVALID_CREDENTIALS,
    "Invalid token type.": ErrorCode.AUTH_INVALID_TOKEN,
    "Invalid or expired token.": ErrorCode.AUTH_INVALID_TOKEN,
    "Invalid or expired refresh token.": ErrorCode.AUTH_INVALID_TOKEN,
    "User not found.": ErrorCode.AUTH_NOT_AUTHENTICATED,
    "Invalid token type. Expected access token.": ErrorCode.AUTH_INVALID_TOKEN,
    "Admin privileges required.": ErrorCode.ADMIN_REQUIRED,
    "Super admin privileges required.": ErrorCode.ADMIN_REQUIRED,
    "Knowledge base not found.": ErrorCode.KB_NOT_FOUND,
    "Document not found.": ErrorCode.DOCUMENT_NOT_FOUND,
    "Session not found.": ErrorCode.SESSION_NOT_FOUND,
    "Task not found.": ErrorCode.VALIDATION_ERROR,
    "User is already a member.": ErrorCode.MEMBER_ALREADY_EXISTS,
    "Member not found.": ErrorCode.MEMBER_NOT_FOUND,
    "Cannot remove the owner.": ErrorCode.PERMISSION_DENIED,
}


def resolve_error_code(detail: str) -> ErrorCode:
    """Resolve an HTTPException detail string to an ErrorCode."""
    if detail in _DETAIL_TO_CODE:
        return _DETAIL_TO_CODE[detail]
    lower = detail.lower()
    if "permission" in lower or "access denied" in lower:
        return ErrorCode.PERMISSION_DENIED
    if "not found" in lower:
        return ErrorCode.VALIDATION_ERROR
    if "limit" in lower or "maximum" in lower:
        return ErrorCode.DOCUMENT_LIMIT_REACHED if "document" in lower else ErrorCode.KB_LIMIT_REACHED
    if "file type" in lower or "unsupported" in lower:
        return ErrorCode.DOCUMENT_INVALID_TYPE
    if "file size" in lower or "too large" in lower:
        return ErrorCode.DOCUMENT_TOO_LARGE
    return ErrorCode.VALIDATION_ERROR


def from_http_detail(detail: object) -> dict:
    """Convert HTTPException.detail to standardized error response."""
    if isinstance(detail, dict) and "code" in detail:
        return detail

    text = str(detail) if detail is not None else ""
    code = resolve_error_code(text)
    return error_response(code, text or None)
