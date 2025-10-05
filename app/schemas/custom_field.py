"""Custom field schemas."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CustomFieldOption(BaseModel):
    id: int | None = None
    value: str
    color: str | None = None
    position: int = 0

    model_config = ConfigDict(from_attributes=True)


class CustomFieldBase(BaseModel):
    name: str
    type: Literal["text", "number", "date", "dropdown", "boolean"]


class CustomFieldCreate(CustomFieldBase):
    project_id: int
    options: list[CustomFieldOption] | None = None


class CustomFieldRead(CustomFieldBase):
    id: int
    project_id: int
    created_at: datetime
    options: list[CustomFieldOption] = []

    model_config = ConfigDict(from_attributes=True)


class CustomFieldValuePayload(BaseModel):
    value_text: str | None = None
    value_number: float | None = None
    value_date: datetime | None = None
    value_boolean: bool | None = None
