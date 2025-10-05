"""Section schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SectionBase(BaseModel):
    name: str
    project_id: int
    position: int = 0


class SectionCreate(SectionBase):
    pass


class SectionUpdate(BaseModel):
    name: str | None = None
    position: int | None = None


class SectionRead(SectionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
