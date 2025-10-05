"""Pydantic schemas used by API responses and requests."""
from pydantic import BaseModel


class Message(BaseModel):
    message: str
