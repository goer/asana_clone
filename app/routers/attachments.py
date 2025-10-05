"""Attachment endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user
from app.db.session import get_db
from app.models.attachment import Attachment
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import UserWorkspace
from app.schemas.attachment import AttachmentCreate, AttachmentRead

router = APIRouter()


def _ensure_task_access(db: Session, user: User, task: Task) -> Project:
    project = db.get(Project, task.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    membership = db.get(UserWorkspace, (user.id, project.workspace_id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of workspace")
    return project


@router.get("/tasks/{task_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttachmentRead]:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _ensure_task_access(db, current_user, task)

    attachments = db.execute(
        select(Attachment)
        .where(Attachment.task_id == task_id)
        .options(selectinload(Attachment.uploader))
        .order_by(Attachment.created_at.asc())
    ).scalars().all()
    return [AttachmentRead.model_validate(attachment) for attachment in attachments]


@router.post("/tasks/{task_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def create_attachment(
    task_id: int,
    payload: AttachmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentRead:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _ensure_task_access(db, current_user, task)

    attachment = Attachment(
        filename=payload.filename,
        url=str(payload.url),
        task_id=task_id if payload.comment_id is None else None,
        comment_id=payload.comment_id,
        uploader_id=current_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    attachment.uploader = current_user
    return AttachmentRead.model_validate(attachment)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    if attachment.task is not None:
        task = attachment.task
    elif attachment.comment is not None:
        task = attachment.comment.task
    else:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment is not linked to a task or comment")

    _ensure_task_access(db, current_user, task)

    db.delete(attachment)
    db.commit()
