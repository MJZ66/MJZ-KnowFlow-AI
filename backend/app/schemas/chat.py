"""Chat session and message schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=300)


class SessionResponse(BaseModel):
    id: int
    knowledge_base_id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = dict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    role: str
    content: str
    created_at: datetime

    model_config = dict(from_attributes=True)


class ReferenceResponse(BaseModel):
    id: int
    source_filename: Optional[str]
    page_number: Optional[int]
    section_title: Optional[str]
    content_preview: Optional[str]
    score: Optional[float]

    model_config = dict(from_attributes=True)


class StreamRequest(BaseModel):
    content: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
