"""API routers exposed by the FastAPI application."""
from fastapi import APIRouter

from app.routers import (
    attachments,
    auth,
    comments,
    custom_fields,
    projects,
    sections,
    tags,
    tasks,
    teams,
    users,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(sections.router, prefix="/sections", tags=["Sections"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(comments.router, tags=["Comments"])
api_router.include_router(attachments.router, tags=["Attachments"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])
api_router.include_router(teams.router, prefix="/teams", tags=["Teams"])
api_router.include_router(custom_fields.router, tags=["Custom Fields"])
