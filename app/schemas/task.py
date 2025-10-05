"""Task schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from pydantic import Field

from app.schemas.project import ProjectRead
from app.schemas.user import UserRead


class TaskBase(BaseModel):
    name: str
    project_id: int
    description: str | None = None
    section_id: int | None = None
    parent_task_id: int | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    position: int = 0


class TaskCreate(TaskBase):
    completed: bool | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    section_id: int | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    completed: bool | None = None
    position: int | None = None


class TaskRead(TaskBase):
    id: int
    assignee: UserRead | None = None
    creator: UserRead | None = None
    project: ProjectRead | None = None
    parent_task: TaskRead | None = Field(default=None, alias="parent", serialization_alias="parent_task")
    completed: bool
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


class PaginatedTasks(BaseModel):
    data: List[TaskRead]
    pagination: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


TaskRead.model_rebuild()
