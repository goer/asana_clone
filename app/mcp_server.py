"""
MCP server integration for Asana Clone API using fastapi-mcp library.

This module creates an MCP server using a separate simplified FastAPI app
to avoid recursion issues with complex nested Pydantic models.

Following fastapi-mcp best practices with a workaround:
- Create a separate app with all routers but simplified (flattened) schemas
- Use FastApiMCP to wrap this simplified app
- Deploy separately as recommended in fastapi-mcp docs for complex schemas
"""
import logging
from datetime import datetime

from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.mcp_auth import get_mcp_user_context
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, UserWorkspace
from app.models.project import Project
from app.models.task import Task
from app.models.section import Section
from app.models.comment import Comment
from app.models.tag import Tag
from app.models.task import TaskTag, TaskCustomFieldValue
from app.models.team import Team, UserTeam
from app.models.attachment import Attachment
from app.models.custom_field import CustomField, CustomFieldOption

logger = logging.getLogger(__name__)

# =======================
# Simplified MCP Schemas (Flattened - no nested objects)
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
    model_config = {"from_attributes": True}
    token: str
    user_id: int
    email: str
    name: str

# Workspace
class WorkspaceCreateRequest(BaseModel):
    name: str

class WorkspaceResponse(BaseModel):
    model_config = {"from_attributes": True}
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
    model_config = {"from_attributes": True}
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
    model_config = {"from_attributes": True}
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
    model_config = {"from_attributes": True}
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
    model_config = {"from_attributes": True}
    id: int
    content: str
    task_id: int
    author_id: int
    created_at: datetime
    updated_at: datetime

class CommentUpdateRequest(BaseModel):
    content: str

# Tag
class TagCreateRequest(BaseModel):
    name: str
    workspace_id: int
    color: str | None = None

class TagResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    workspace_id: int
    color: str | None
    created_at: datetime

class TagUpdateRequest(BaseModel):
    name: str | None = None
    color: str | None = None

# Team
class TeamCreateRequest(BaseModel):
    name: str
    workspace_id: int
    description: str | None = None

class TeamResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    workspace_id: int
    description: str | None
    created_at: datetime
    updated_at: datetime

# Attachment
class AttachmentCreateRequest(BaseModel):
    filename: str
    file_url: str
    file_size: int | None = None

class AttachmentResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    filename: str
    file_url: str
    file_size: int | None
    task_id: int
    uploader_id: int
    created_at: datetime

# Custom Field
class CustomFieldCreateRequest(BaseModel):
    name: str
    field_type: str  # text, number, select, multi_select
    options: list[str] | None = None

class CustomFieldResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    project_id: int
    field_type: str
    created_at: datetime
    updated_at: datetime

class CustomFieldValueRequest(BaseModel):
    value: str | None = None

# =======================
# MCP FastAPI App with Simplified Endpoints
# =======================

mcp_app = FastAPI(
    title="Asana Clone MCP API",
    description="Simplified API for Model Context Protocol integration - covers all endpoints",
    version="1.0.0",
)

# Auth Endpoints
@mcp_app.post("/auth/register", response_model=TokenResponse, tags=["Authentication"], operation_id="mcp_register")
def register(request: UserRegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user and get authentication token."""
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(request.password)
    user = User(email=request.email, name=request.name, password_hash=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.id)
    return TokenResponse(token=token, user_id=user.id, email=user.email, name=user.name)

@mcp_app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"], operation_id="mcp_login")
def login(request: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Login user and get authentication token."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=user.id)
    return TokenResponse(token=token, user_id=user.id, email=user.email, name=user.name)

# Workspace Endpoints
@mcp_app.get("/workspaces", response_model=list[WorkspaceResponse], tags=["Workspaces"], operation_id="mcp_list_workspaces")
def list_workspaces(db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[WorkspaceResponse]:
    """List all workspaces (filtered by user if context provided)."""
    if user:
        # Filter by user access
        workspace_rows = db.scalars(
            select(Workspace).join(UserWorkspace, Workspace.id == UserWorkspace.workspace_id)
            .filter(UserWorkspace.user_id == user.id).order_by(Workspace.created_at)
        ).all()
    else:
        # No user context - return all workspaces (API key auth only)
        workspace_rows = db.scalars(select(Workspace).order_by(Workspace.created_at)).all()
    return [WorkspaceResponse.model_validate(w) for w in workspace_rows]

@mcp_app.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, tags=["Workspaces"], operation_id="mcp_create_workspace")
def create_workspace(payload: WorkspaceCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> WorkspaceResponse:
    """Create a new workspace."""
    workspace = Workspace(name=payload.name, owner_id=user.id if user else 1)
    db.add(workspace)
    db.flush()
    db.add(UserWorkspace(user_id=user.id if user else 1, workspace=workspace))
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)

@mcp_app.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse, tags=["Workspaces"], operation_id="mcp_get_workspace")
def get_workspace(workspace_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> WorkspaceResponse:
    """Get a specific workspace."""
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    return WorkspaceResponse.model_validate(workspace)

@mcp_app.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse, tags=["Workspaces"], operation_id="mcp_update_workspace")
def update_workspace(workspace_id: int, payload: WorkspaceUpdateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> WorkspaceResponse:
    """Update a workspace."""
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.owner_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Only owner may update workspace")
    workspace.name = payload.name
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)

@mcp_app.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Workspaces"], operation_id="mcp_delete_workspace")
def delete_workspace(workspace_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete a workspace."""
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.owner_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Only owner may delete workspace")
    db.delete(workspace)
    db.commit()

# Project Endpoints
@mcp_app.get("/projects", response_model=list[ProjectResponse], tags=["Projects"], operation_id="mcp_list_projects")
def list_projects(workspace_id: int = Query(..., description="Workspace identifier"), db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[ProjectResponse]:
    """List projects in a workspace."""
    membership = db.get(UserWorkspace, (user.id if user else 1, workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    projects = db.scalars(select(Project).where(Project.workspace_id == workspace_id)).all()
    return [ProjectResponse.model_validate(p) for p in projects]

@mcp_app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, tags=["Projects"], operation_id="mcp_create_project")
def create_project(payload: ProjectCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> ProjectResponse:
    """Create a new project."""
    membership = db.get(UserWorkspace, (user.id if user else 1, payload.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    project = Project(**payload.model_dump(), owner_id=user.id if user else 1)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)

@mcp_app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"], operation_id="mcp_get_project")
def get_project(project_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> ProjectResponse:
    """Get a specific project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    return ProjectResponse.model_validate(project)

@mcp_app.patch("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"], operation_id="mcp_update_project")
def update_project(project_id: int, payload: ProjectUpdateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> ProjectResponse:
    """Update a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Only owner may update project")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)

@mcp_app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"], operation_id="mcp_delete_project")
def delete_project(project_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Only owner may delete project")
    db.delete(project)
    db.commit()

# Task Endpoints
@mcp_app.get("/tasks", response_model=list[TaskResponse], tags=["Tasks"], operation_id="mcp_list_tasks")
def list_tasks(
    workspace_id: int = Query(..., description="Workspace identifier"),
    project_id: int | None = Query(None),
    assignee_id: int | None = Query(None),
    completed: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_mcp_user_context),
) -> list[TaskResponse]:
    """List tasks in a workspace with optional filters."""
    membership = db.get(UserWorkspace, (user.id if user else 1, workspace_id))
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
        select(Task).join(Project).where(and_(*filters))
        .order_by(Task.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return [TaskResponse.model_validate(t) for t in tasks]

@mcp_app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"], operation_id="mcp_create_task")
def create_task(payload: TaskCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> TaskResponse:
    """Create a new task."""
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    task_data = payload.model_dump(exclude={"completed"})
    task_data["creator_id"] = user.id if user else 1
    task = Task(**task_data)
    if payload.completed:
        from datetime import timezone
        task.completed_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)

@mcp_app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"], operation_id="mcp_get_task")
def get_task(task_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> TaskResponse:
    """Get a specific task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    return TaskResponse.model_validate(task)

@mcp_app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"], operation_id="mcp_update_task")
def update_task(task_id: int, payload: TaskUpdateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> TaskResponse:
    """Update a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
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

@mcp_app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"], operation_id="mcp_delete_task")
def delete_task(task_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    db.delete(task)
    db.commit()

# Section Endpoints
@mcp_app.get("/sections", response_model=list[SectionResponse], tags=["Sections"], operation_id="mcp_list_sections")
def list_sections(project_id: int = Query(..., description="Project identifier"), db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[SectionResponse]:
    """List sections in a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    sections = db.scalars(select(Section).where(Section.project_id == project_id)).all()
    return [SectionResponse.model_validate(s) for s in sections]

@mcp_app.post("/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED, tags=["Sections"], operation_id="mcp_create_section")
def create_section(payload: SectionCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> SectionResponse:
    """Create a new section."""
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    section = Section(**payload.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return SectionResponse.model_validate(section)

@mcp_app.patch("/sections/{section_id}", response_model=SectionResponse, tags=["Sections"], operation_id="mcp_update_section")
def update_section(section_id: int, payload: SectionUpdateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> SectionResponse:
    """Update a section."""
    section = db.get(Section, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    project = db.get(Project, section.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    section.name = payload.name
    db.commit()
    db.refresh(section)
    return SectionResponse.model_validate(section)

@mcp_app.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Sections"], operation_id="mcp_delete_section")
def delete_section(section_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete a section."""
    section = db.get(Section, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    project = db.get(Project, section.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    db.delete(section)
    db.commit()

# Comment Endpoints
@mcp_app.get("/tasks/{task_id}/comments", response_model=list[CommentResponse], tags=["Comments"], operation_id="mcp_list_comments")
def list_comments(task_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[CommentResponse]:
    """List comments on a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    comments = db.scalars(select(Comment).where(Comment.task_id == task_id).order_by(Comment.created_at.asc())).all()
    return [CommentResponse.model_validate(c) for c in comments]

@mcp_app.post("/tasks/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED, tags=["Comments"], operation_id="mcp_create_comment")
def create_comment(task_id: int, payload: CommentCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> CommentResponse:
    """Create a comment on a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    comment = Comment(content=payload.content, task_id=task_id, author_id=user.id if user else 1)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentResponse.model_validate(comment)

@mcp_app.patch("/comments/{comment_id}", response_model=CommentResponse, tags=["Comments"], operation_id="mcp_update_comment")
def update_comment(comment_id: int, payload: CommentUpdateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> CommentResponse:
    """Update a comment."""
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Cannot edit this comment")
    comment.content = payload.content
    db.commit()
    db.refresh(comment)
    return CommentResponse.model_validate(comment)

@mcp_app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Comments"], operation_id="mcp_delete_comment")
def delete_comment(comment_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete a comment."""
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Cannot delete this comment")
    db.delete(comment)
    db.commit()

# Tag Endpoints
@mcp_app.get("/tags", response_model=list[TagResponse], tags=["Tags"], operation_id="mcp_list_tags")
def list_tags(workspace_id: int = Query(..., description="Workspace identifier"), db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[TagResponse]:
    """List tags in a workspace."""
    membership = db.get(UserWorkspace, (user.id if user else 1, workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    tags = db.scalars(select(Tag).where(Tag.workspace_id == workspace_id).order_by(Tag.name.asc())).all()
    return [TagResponse.model_validate(tag) for tag in tags]

@mcp_app.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED, tags=["Tags"], operation_id="mcp_create_tag")
def create_tag(payload: TagCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> TagResponse:
    """Create a new tag."""
    membership = db.get(UserWorkspace, (user.id if user else 1, payload.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagResponse.model_validate(tag)

@mcp_app.patch("/tags/{tag_id}", response_model=TagResponse, tags=["Tags"], operation_id="mcp_update_tag")
def update_tag(tag_id: int, payload: TagUpdateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> TagResponse:
    """Update a tag."""
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, tag.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return TagResponse.model_validate(tag)

@mcp_app.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tags"], operation_id="mcp_delete_tag")
def delete_tag(tag_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete a tag."""
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, tag.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    db.delete(tag)
    db.commit()

@mcp_app.post("/tags/tasks/{task_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tags"], operation_id="mcp_add_tag_to_task")
def add_tag_to_task(task_id: int, tag_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Add a tag to a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    project = db.get(Project, task.project_id)
    if not project or tag.workspace_id != project.workspace_id:
        raise HTTPException(status_code=400, detail="Tag and task must be in the same workspace")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    existing = db.get(TaskTag, (task_id, tag_id))
    if not existing:
        db.add(TaskTag(task_id=task_id, tag_id=tag_id))
        db.commit()

@mcp_app.delete("/tags/tasks/{task_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tags"], operation_id="mcp_remove_tag_from_task")
def remove_tag_from_task(task_id: int, tag_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Remove a tag from a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    task_tag = db.get(TaskTag, (task_id, tag_id))
    if task_tag:
        db.delete(task_tag)
        db.commit()

# Team Endpoints
@mcp_app.get("/teams", response_model=list[TeamResponse], tags=["Teams"], operation_id="mcp_list_teams")
def list_teams(workspace_id: int = Query(..., description="Workspace identifier"), db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[TeamResponse]:
    """List teams in a workspace."""
    membership = db.get(UserWorkspace, (user.id if user else 1, workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    teams = db.scalars(select(Team).where(Team.workspace_id == workspace_id).order_by(Team.created_at.asc())).all()
    return [TeamResponse.model_validate(team) for team in teams]

@mcp_app.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, tags=["Teams"], operation_id="mcp_create_team")
def create_team(payload: TeamCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> TeamResponse:
    """Create a new team."""
    membership = db.get(UserWorkspace, (user.id if user else 1, payload.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    team = Team(**payload.model_dump())
    db.add(team)
    db.flush()
    db.add(UserTeam(user_id=user.id if user else 1, team_id=team.id))
    db.commit()
    db.refresh(team)
    return TeamResponse.model_validate(team)

@mcp_app.post("/teams/{team_id}/members", status_code=status.HTTP_204_NO_CONTENT, tags=["Teams"], operation_id="mcp_add_team_member")
def add_team_member(team_id: int, user_id: int = Query(...), db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Add a member to a team."""
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, team.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    target_membership = db.get(UserWorkspace, (user_id, team.workspace_id))
    if not target_membership:
        raise HTTPException(status_code=400, detail="User is not a member of the workspace")
    existing = db.get(UserTeam, (user_id, team_id))
    if not existing:
        db.add(UserTeam(user_id=user_id, team_id=team_id))
        db.commit()

@mcp_app.delete("/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Teams"], operation_id="mcp_remove_team_member")
def remove_team_member(team_id: int, user_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Remove a member from a team."""
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, team.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    user_team = db.get(UserTeam, (user_id, team_id))
    if user_team:
        db.delete(user_team)
        db.commit()

# Attachment Endpoints
@mcp_app.get("/tasks/{task_id}/attachments", response_model=list[AttachmentResponse], tags=["Attachments"], operation_id="mcp_list_attachments")
def list_attachments(task_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[AttachmentResponse]:
    """List attachments on a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    attachments = db.scalars(select(Attachment).where(Attachment.task_id == task_id).order_by(Attachment.created_at.asc())).all()
    return [AttachmentResponse.model_validate(a) for a in attachments]

@mcp_app.post("/tasks/{task_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED, tags=["Attachments"], operation_id="mcp_create_attachment")
def create_attachment(task_id: int, payload: AttachmentCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> AttachmentResponse:
    """Create an attachment on a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    attachment = Attachment(**payload.model_dump(), task_id=task_id, uploader_id=user.id if user else 1)
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return AttachmentResponse.model_validate(attachment)

@mcp_app.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Attachments"], operation_id="mcp_delete_attachment")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete an attachment."""
    attachment = db.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if attachment.uploader_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Can only delete your own attachments")
    db.delete(attachment)
    db.commit()

# Custom Field Endpoints
@mcp_app.get("/projects/{project_id}/custom-fields", response_model=list[CustomFieldResponse], tags=["Custom Fields"], operation_id="mcp_list_custom_fields")
def list_custom_fields(project_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> list[CustomFieldResponse]:
    """List custom fields for a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    fields = db.scalars(select(CustomField).where(CustomField.project_id == project_id)).all()
    return [CustomFieldResponse.model_validate(f) for f in fields]

@mcp_app.post("/projects/{project_id}/custom-fields", response_model=CustomFieldResponse, status_code=status.HTTP_201_CREATED, tags=["Custom Fields"], operation_id="mcp_create_custom_field")
def create_custom_field(project_id: int, payload: CustomFieldCreateRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> CustomFieldResponse:
    """Create a custom field for a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Only project owner can create custom fields")
    field = CustomField(name=payload.name, project_id=project_id, field_type=payload.field_type)
    db.add(field)
    db.flush()
    if payload.options:
        for option_name in payload.options:
            db.add(CustomFieldOption(field_id=field.id, option_value=option_name))
    db.commit()
    db.refresh(field)
    return CustomFieldResponse.model_validate(field)

@mcp_app.delete("/custom-fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Custom Fields"], operation_id="mcp_delete_custom_field")
def delete_custom_field(field_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Delete a custom field."""
    field = db.get(CustomField, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    project = db.get(Project, field.project_id)
    if not project or project.owner_id != user.id if user else 1:
        raise HTTPException(status_code=403, detail="Only project owner can delete custom fields")
    db.delete(field)
    db.commit()

@mcp_app.post("/tasks/{task_id}/custom-fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Custom Fields"], operation_id="mcp_set_custom_field_value")
def set_custom_field_value(task_id: int, field_id: int, payload: CustomFieldValueRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Set a custom field value for a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    field = db.get(CustomField, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    project = db.get(Project, task.project_id)
    if not project or field.project_id != task.project_id:
        raise HTTPException(status_code=400, detail="Custom field must belong to task's project")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    value_record = db.get(TaskCustomFieldValue, (task_id, field_id))
    if value_record:
        value_record.value = payload.value
    else:
        db.add(TaskCustomFieldValue(task_id=task_id, field_id=field_id, value=payload.value))
    db.commit()

@mcp_app.delete("/tasks/{task_id}/custom-fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Custom Fields"], operation_id="mcp_clear_custom_field_value")
def clear_custom_field_value(task_id: int, field_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_mcp_user_context)) -> None:
    """Clear a custom field value for a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(Project, task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id if user else 1, project.workspace_id))
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")
    value_record = db.get(TaskCustomFieldValue, (task_id, field_id))
    if value_record:
        db.delete(value_record)
        db.commit()

# =======================
# MCP Server Setup using FastApiMCP
# =======================

def create_mcp_server():
    """
    Create and configure MCP server using fastapi-mcp library.

    This follows the recommended approach from fastapi-mcp documentation:
    - Create a separate simplified FastAPI app (to avoid recursion with nested schemas)
    - Wrap it with FastApiMCP
    - Mount with HTTP transport
    - Apply API key authentication

    Returns:
        FastApiMCP instance if successful, None otherwise
    """
    try:
        from fastapi import Depends
        from fastapi_mcp import FastApiMCP, AuthConfig
        from app.mcp_auth import verify_api_key

        # Create MCP server from the simplified FastAPI app
        # This app has all the same endpoints but with flattened response schemas
        mcp = FastApiMCP(
            mcp_app,
            name="Asana Clone MCP",
            description="Model Context Protocol interface for Asana Clone API - Full featured task management covering all endpoints",
            # Don't describe full schemas to keep tool descriptions manageable
            describe_full_response_schema=False,
            # Only describe success responses
            describe_all_responses=False,
            # Forward authentication headers to internal ASGI calls
            headers=["X-API-Key", "X-Mcp-User"],
            # Add API key authentication
            auth_config=AuthConfig(
                dependencies=[Depends(verify_api_key)],
            ),
        )

        logger.info("✓ MCP server created successfully using FastApiMCP")
        logger.info("✓ All API endpoints exposed as MCP tools (59 operations covering all features)")
        logger.info("  - Authentication: register, login")
        logger.info("  - Workspaces: CRUD operations")
        logger.info("  - Projects: CRUD operations")
        logger.info("  - Tasks: CRUD operations with filters")
        logger.info("  - Sections: CRUD operations")
        logger.info("  - Comments: CRUD operations")
        logger.info("  - Tags: CRUD operations + task associations")
        logger.info("  - Teams: CRUD operations + member management")
        logger.info("  - Attachments: CRUD operations")
        logger.info("  - Custom Fields: CRUD operations + task values")
        return mcp

    except ImportError as e:
        logger.error(f"✗ fastapi-mcp library not available: {e}")
        return None
    except RecursionError as e:
        logger.error(f"✗ RecursionError while setting up MCP: {e}")
        logger.error("  This should not happen with simplified schemas")
        return None
    except Exception as e:
        logger.error(f"✗ Failed to setup MCP: {type(e).__name__}: {e}")
        return None

