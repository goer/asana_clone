"""Workspace schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead


class WorkspaceBase(BaseModel):
    name: str


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = None


class WorkspaceRead(WorkspaceBase):
    id: int
    owner: UserRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
