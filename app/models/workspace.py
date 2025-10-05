"""Workspace model and membership relationships."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="owned_workspaces")
    teams = relationship("Team", back_populates="workspace", cascade="all,delete-orphan")
    projects = relationship("Project", back_populates="workspace", cascade="all,delete-orphan")
    memberships = relationship("UserWorkspace", back_populates="workspace", cascade="all,delete-orphan")
    tags = relationship("Tag", back_populates="workspace", cascade="all,delete-orphan")


class UserWorkspace(Base):
    __tablename__ = "user_workspaces"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User", back_populates="memberships")
    workspace = relationship("Workspace", back_populates="memberships")
