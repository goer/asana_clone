"""Project schemas."""
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead
from app.schemas.workspace import WorkspaceRead


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    workspace_id: int
    team_id: int | None = None
    is_public: bool = True


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    team_id: int | None = None
    is_public: bool | None = None


class ProjectRead(ProjectBase):
    id: int
    owner: UserRead | None = None
    workspace: WorkspaceRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectList(BaseModel):
    items: List[ProjectRead]
    total: int

    model_config = ConfigDict(from_attributes=True)
