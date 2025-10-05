"""Workspace endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import UserWorkspace, Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate

router = APIRouter()


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[WorkspaceRead]:
    """Return workspaces the user belongs to."""
    workspace_rows = db.scalars(
        select(Workspace)
        .join(UserWorkspace, Workspace.id == UserWorkspace.workspace_id)
        .filter(UserWorkspace.user_id == current_user.id)
        .options(selectinload(Workspace.owner))
        .order_by(Workspace.created_at)
    ).all()
    return [WorkspaceRead.model_validate(w) for w in workspace_rows]


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceRead:
    """Create a new workspace and add the owner as a member."""
    workspace = Workspace(name=payload.name, owner_id=current_user.id)
    db.add(workspace)
    db.flush()
    db.add(UserWorkspace(user_id=current_user.id, workspace=workspace))
    workspace.owner = current_user
    db.commit()
    db.refresh(workspace)
    return WorkspaceRead.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def read_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceRead:
    """Return a workspace if the user is a member."""
    workspace_stmt = (
        select(Workspace)
        .where(Workspace.id == workspace_id)
        .options(selectinload(Workspace.owner))
    )
    workspace = db.scalars(workspace_stmt).first()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    membership = db.get(UserWorkspace, (current_user.id, workspace_id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of workspace")
    return WorkspaceRead.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceRead:
    """Update workspace metadata."""
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if workspace.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner may update workspace")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)
    return WorkspaceRead.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a workspace owned by the current user."""
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if workspace.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner may delete workspace")

    db.delete(workspace)
    db.commit()
