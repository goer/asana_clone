"""
MCP server integration for Asana Clone API.

This module creates a separate FastAPI app with simplified endpoints to avoid
recursion issues when processing deeply nested Pydantic models.
The main API's complex schemas (TaskRead → ProjectRead → WorkspaceRead → UserRead)
cause infinite recursion in fastapi-mcp's OpenAPI schema processor.

Solution: Create a parallel MCP-specific app with flattened response models.
"""
import logging
from typing import Any
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, UserWorkspace
from app.models.project import Project
from app.models.task import Task
from app.models.section import Section
from app.models.comment import Comment

logger = logging.getLogger(__name__)

# =======================
# Simplified MCP Schemas
# =======================

# Auth
class UserRegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    token: str
    user_id: int
    email: str
    name: str

# Workspace
class WorkspaceCreateRequest(BaseModel):
    name: str

class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    updated_at: datetime

class WorkspaceUpdateRequest(BaseModel):
    name: str

# Project
class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
    workspace_id: int
    is_public: bool = True

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    workspace_id: int
    owner_id: int
    is_public: bool
    created_at: datetime
    updated_at: datetime

class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None

# Task
class TaskCreateRequest(BaseModel):
    name: str
    project_id: int
    description: str | None = None
    section_id: int | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    completed: bool = False

class TaskResponse(BaseModel):
    id: int
    name: str
    description: str | None
    project_id: int
    section_id: int | None
    assignee_id: int | None
    creator_id: int
    due_date: datetime | None
    completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

class TaskUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    section_id: int | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    completed: bool | None = None

# Section
class SectionCreateRequest(BaseModel):
    name: str
    project_id: int

class SectionResponse(BaseModel):
    id: int
    name: str
    project_id: int
    created_at: datetime
    updated_at: datetime

class SectionUpdateRequest(BaseModel):
    name: str

# Comment
class CommentCreateRequest(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    content: str
    task_id: int
    author_id: int
    created_at: datetime
    updated_at: datetime

class CommentUpdateRequest(BaseModel):
    content: str

# =======================
# MCP FastAPI App
# =======================

mcp_app = FastAPI(
    title="Asana Clone MCP API",
    description="Simplified API for Model Context Protocol integration",
    version="1.0.0",
)

# =======================
# Auth Endpoints
# =======================

@mcp_app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"])
def register(request: UserRegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user."""
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(request.password)
    user = User(email=request.email, name=request.name, password_hash=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)

    return TokenResponse(
        token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )

@mcp_app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(request: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Login user."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=user.id)

    return TokenResponse(
        token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )

# =======================
# Workspace Endpoints
# =======================

@mcp_app.get("/workspaces", response_model=list[WorkspaceResponse], tags=["Workspaces"])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[WorkspaceResponse]:
    """List all workspaces for the current user."""
    workspace_rows = db.scalars(
        select(Workspace)
        .join(UserWorkspace, Workspace.id == UserWorkspace.workspace_id)
        .filter(UserWorkspace.user_id == current_user.id)
        .order_by(Workspace.created_at)
    ).all()
    return [WorkspaceResponse.model_validate(w) for w in workspace_rows]

@mcp_app.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, tags=["Workspaces"])
def create_workspace(
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    """Create a new workspace."""
    workspace = Workspace(name=payload.name, owner_id=current_user.id)
    db.add(workspace)
    db.flush()
    db.add(UserWorkspace(user_id=current_user.id, workspace=workspace))
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)

@mcp_app.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse, tags=["Workspaces"])
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    """Get a specific workspace."""
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    membership = db.get(UserWorkspace, (current_user.id, workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    return WorkspaceResponse.model_validate(workspace)

@mcp_app.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse, tags=["Workspaces"])
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    """Update a workspace."""
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner may update workspace")

    workspace.name = payload.name
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)

@mcp_app.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Workspaces"])
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a workspace."""
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner may delete workspace")

    db.delete(workspace)
    db.commit()

# =======================
# Project Endpoints
# =======================

@mcp_app.get("/projects", response_model=list[ProjectResponse], tags=["Projects"])
def list_projects(
    workspace_id: int = Query(..., description="Workspace identifier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    """List projects in a workspace."""
    membership = db.get(UserWorkspace, (current_user.id, workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    projects = db.scalars(
        select(Project).where(Project.workspace_id == workspace_id)
    ).all()
    return [ProjectResponse.model_validate(p) for p in projects]

@mcp_app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, tags=["Projects"])
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Create a new project."""
    membership = db.get(UserWorkspace, (current_user.id, payload.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    project = Project(**payload.model_dump(), owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)

@mcp_app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Get a specific project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    return ProjectResponse.model_validate(project)

@mcp_app.patch("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Update a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner may update project")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)

@mcp_app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"])
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner may delete project")

    db.delete(project)
    db.commit()

# =======================
# Task Endpoints
# =======================

@mcp_app.get("/tasks", response_model=list[TaskResponse], tags=["Tasks"])
def list_tasks(
    workspace_id: int = Query(..., description="Workspace identifier"),
    project_id: int | None = Query(None),
    assignee_id: int | None = Query(None),
    completed: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    """List tasks in a workspace."""
    membership = db.get(UserWorkspace, (current_user.id, workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    filters = [Project.workspace_id == workspace_id]
    if project_id:
        filters.append(Task.project_id == project_id)
    if assignee_id:
        filters.append(Task.assignee_id == assignee_id)
    if completed is not None:
        condition = Task.completed_at.isnot(None) if completed else Task.completed_at.is_(None)
        filters.append(condition)

    tasks = db.scalars(
        select(Task)
        .join(Project)
        .where(and_(*filters))
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [TaskResponse.model_validate(t) for t in tasks]

@mcp_app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
def create_task(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """Create a new task."""
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    task_data = payload.model_dump(exclude={"completed"})
    task_data["creator_id"] = current_user.id
    task = Task(**task_data)

    if payload.completed:
        from datetime import timezone
        task.completed_at = datetime.now(timezone.utc)

    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)

@mcp_app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """Get a specific task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    return TaskResponse.model_validate(task)

@mcp_app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def update_task(
    task_id: int,
    payload: TaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """Update a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    update_data = payload.model_dump(exclude_none=True)
    completed_flag = update_data.pop("completed", None)

    for field, value in update_data.items():
        setattr(task, field, value)

    if completed_flag is not None:
        from datetime import timezone
        task.completed_at = datetime.now(timezone.utc) if completed_flag else None

    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)

@mcp_app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    db.delete(task)
    db.commit()

# =======================
# Section Endpoints
# =======================

@mcp_app.get("/sections", response_model=list[SectionResponse], tags=["Sections"])
def list_sections(
    project_id: int = Query(..., description="Project identifier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SectionResponse]:
    """List sections in a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    sections = db.scalars(select(Section).where(Section.project_id == project_id)).all()
    return [SectionResponse.model_validate(s) for s in sections]

@mcp_app.post("/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED, tags=["Sections"])
def create_section(
    payload: SectionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SectionResponse:
    """Create a new section."""
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    section = Section(**payload.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return SectionResponse.model_validate(section)

@mcp_app.patch("/sections/{section_id}", response_model=SectionResponse, tags=["Sections"])
def update_section(
    section_id: int,
    payload: SectionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SectionResponse:
    """Update a section."""
    section = db.get(Section, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    project = db.get(Project, section.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    section.name = payload.name
    db.commit()
    db.refresh(section)
    return SectionResponse.model_validate(section)

@mcp_app.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Sections"])
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a section."""
    section = db.get(Section, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    project = db.get(Project, section.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    db.delete(section)
    db.commit()

# =======================
# Comment Endpoints
# =======================

@mcp_app.get("/tasks/{task_id}/comments", response_model=list[CommentResponse], tags=["Comments"])
def list_comments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CommentResponse]:
    """List comments on a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    comments = db.scalars(
        select(Comment)
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
    ).all()
    return [CommentResponse.model_validate(c) for c in comments]

@mcp_app.post("/tasks/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED, tags=["Comments"])
def create_comment(
    task_id: int,
    payload: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Create a comment on a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = db.get(UserWorkspace, (current_user.id, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    comment = Comment(content=payload.content, task_id=task_id, author_id=current_user.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentResponse.model_validate(comment)

@mcp_app.patch("/comments/{comment_id}", response_model=CommentResponse, tags=["Comments"])
def update_comment(
    comment_id: int,
    payload: CommentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Update a comment."""
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot edit this comment")

    comment.content = payload.content
    db.commit()
    db.refresh(comment)
    return CommentResponse.model_validate(comment)

@mcp_app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Comments"])
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a comment."""
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete this comment")

    db.delete(comment)
    db.commit()

# =======================
# MCP Server Setup
# =======================

def create_mcp_server() -> FastAPI | None:
    """
    Create and configure MCP server with transports and API key authentication.

    Returns the MCP FastAPI app if setup succeeds, None otherwise.
    """
    try:
        from fastapi import Depends
        from fastapi_mcp import FastApiMCP, AuthConfig
        from app.mcp_auth import verify_api_key

        # Create MCP server from the simplified app
        mcp = FastApiMCP(
            mcp_app,
            name="Asana Clone MCP",
            description="Model Context Protocol interface for Asana Clone API",
            describe_full_response_schema=False,
            describe_all_responses=False,
            auth_config=AuthConfig(
                dependencies=[Depends(verify_api_key)],
            ),
        )

        # Mount transports
        mcp.mount_http()
        mcp.mount_sse()

        logger.info("✓ MCP server created successfully with HTTP and SSE transports + API key auth")
        logger.info("✓ Exposed endpoints: workspaces, projects, tasks, sections, comments")
        return mcp_app

    except RecursionError as e:
        logger.error(f"✗ RecursionError while setting up MCP: {e}")
        return None
    except Exception as e:
        logger.error(f"✗ Failed to setup MCP: {type(e).__name__}: {e}")
        return None
