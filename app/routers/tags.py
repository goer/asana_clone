"""Tag management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.db.session import get_db
from app.models.tag import Tag
from app.models.task import Task, TaskTag
from app.models.user import User
from app.models.workspace import UserWorkspace
from app.schemas.tag import TagCreate, TagRead, TagUpdate

router = APIRouter()


def _ensure_workspace_membership(db: Session, workspace_id: int, user_id: int) -> None:
    if db.get(UserWorkspace, (user_id, workspace_id)) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of workspace")


@router.get("", response_model=list[TagRead])
def list_tags(
    workspace_id: int = Query(..., description="Workspace identifier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TagRead]:
    _ensure_workspace_membership(db, workspace_id, current_user.id)

    tags = db.scalars(select(Tag).where(Tag.workspace_id == workspace_id).order_by(Tag.name.asc())).all()
    return [TagRead.model_validate(tag) for tag in tags]


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRead:
    _ensure_workspace_membership(db, payload.workspace_id, current_user.id)

    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagRead.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRead:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    _ensure_workspace_membership(db, tag.workspace_id, current_user.id)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return TagRead.model_validate(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    _ensure_workspace_membership(db, tag.workspace_id, current_user.id)

    db.delete(tag)
    db.commit()


@router.post("/tasks/{task_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_tag_to_task(
    task_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    _ensure_workspace_membership(db, tag.workspace_id, current_user.id)
    if task.project.workspace_id != tag.workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag and task must belong to same workspace")

    db.merge(TaskTag(task_id=task_id, tag_id=tag_id))
    db.commit()


@router.delete("/tasks/{task_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_tag_from_task(
    task_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    _ensure_workspace_membership(db, tag.workspace_id, current_user.id)
    mapping = db.get(TaskTag, (task_id, tag_id))
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not assigned to task")

    db.delete(mapping)
    db.commit()
