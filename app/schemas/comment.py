"""Comment schemas."""
from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.user import UserRead


class CommentBase(BaseModel):
    content: str = Field(validation_alias=AliasChoices("text", "content"), serialization_alias="text")
    task_id: int


class CommentCreate(CommentBase):
    author_id: int


class CommentUpdate(BaseModel):
    content: str | None = Field(
        default=None,
        validation_alias=AliasChoices("text", "content"),
        serialization_alias="text",
    )


class CommentRead(CommentBase):
    id: int
    author_id: int
    author: UserRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CommentBody(BaseModel):
    content: str = Field(validation_alias=AliasChoices("text", "content"), serialization_alias="text")

    model_config = ConfigDict(populate_by_name=True)
