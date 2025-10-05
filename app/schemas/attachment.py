"""Attachment schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl

from app.schemas.user import UserRead


class AttachmentBase(BaseModel):
    filename: str
    url: HttpUrl


class AttachmentCreate(AttachmentBase):
    comment_id: int | None = None


class AttachmentRead(AttachmentBase):
    id: int
    task_id: int | None = None
    comment_id: int | None = None
    uploader: UserRead | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
