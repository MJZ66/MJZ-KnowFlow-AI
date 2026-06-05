"""Admin API response schemas."""

from pydantic import BaseModel, Field


class AdminUserItem(BaseModel):
    id: int
    email: str
    username: str
    role: str
    created_at: str
    last_login_at: str | None = None
    last_active_at: str | None = None
    is_online: bool = False
    is_test_account: bool = False


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    online_count: int
    test_account_count: int = 0


class DailyActivePoint(BaseModel):
    date: str
    count: int


class AdminAnalyticsResponse(BaseModel):
    total_users: int
    online_count: int
    dau_today: int
    daily_active: list[DailyActivePoint] = Field(default_factory=list)
    online_threshold_minutes: int


class AdminSystemStatusResponse(BaseModel):
    users: int
    knowledge_bases: int
    documents: int
    chat_sessions: int
    active_tasks: int
    online_count: int
    dau_today: int
    test_users: int = 0


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(user|admin|super_admin)$")
