"""Tag schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    name: str
    workspace_id: int
    color: str | None = None


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class TagRead(TagBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
