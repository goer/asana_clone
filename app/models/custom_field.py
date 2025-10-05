"""Custom field models."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class CustomField(Base):
    __tablename__ = "custom_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="custom_fields")
    options = relationship("CustomFieldOption", back_populates="custom_field", cascade="all,delete-orphan")
    values = relationship("TaskCustomFieldValue", back_populates="custom_field")


class CustomFieldOption(Base):
    __tablename__ = "custom_field_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    custom_field_id: Mapped[int] = mapped_column(ForeignKey("custom_fields.id", ondelete="CASCADE"), nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    custom_field = relationship("CustomField", back_populates="options")
