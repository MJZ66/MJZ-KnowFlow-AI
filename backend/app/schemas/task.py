"""Background task schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: int
    task_type: str
    status: str
    related_document_id: Optional[int]
    progress: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = dict(from_attributes=True)
