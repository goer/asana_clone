"""Team schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead


class TeamBase(BaseModel):
    name: str
    workspace_id: int


class TeamCreate(TeamBase):
    pass


class TeamRead(TeamBase):
    id: int
    created_at: datetime
    members: list[UserRead] = []

    model_config = ConfigDict(from_attributes=True)


class TeamMemberUpdate(BaseModel):
    user_id: int
