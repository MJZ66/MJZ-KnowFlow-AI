"""Knowledge base schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    visibility: str = Field(default="private")  # private, team, public


class KBUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    visibility: Optional[str] = None


class KBResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str
    visibility: str
    created_at: datetime
    updated_at: datetime

    model_config = dict(from_attributes=True)


class PaginatedKBList(BaseModel):
    items: list[KBResponse]
    total: int
    skip: int
    limit: int


class MemberAdd(BaseModel):
    user_id: int
    role: str = Field(default="viewer")  # owner, editor, viewer


class MemberResponse(BaseModel):
    id: int
    knowledge_base_id: int
    user_id: int
    role: str
    created_at: datetime

    model_config = dict(from_attributes=True)
