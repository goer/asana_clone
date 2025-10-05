"""Custom field endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user
from app.db.session import get_db
from app.models.custom_field import CustomField, CustomFieldOption
from app.models.project import Project
from app.models.task import Task, TaskCustomFieldValue
from app.models.user import User
from app.models.workspace import UserWorkspace
from app.schemas.custom_field import (
    CustomFieldCreate,
    CustomFieldOption as CustomFieldOptionSchema,
    CustomFieldRead,
    CustomFieldValuePayload,
)

router = APIRouter()


def _ensure_project_access(db: Session, project_id: int, user_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if db.get(UserWorkspace, (user_id, project.workspace_id)) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of workspace")
    return project


def _ensure_task_access(db: Session, task_id: int, user_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _ensure_project_access(db, task.project_id, user_id)
    return task


def _fetch_field(db: Session, field_id: int) -> CustomField | None:
    return db.scalar(
        select(CustomField)
        .where(CustomField.id == field_id)
        .options(selectinload(CustomField.options))
    )


def _serialize_field(field: CustomField) -> CustomFieldRead:
    return CustomFieldRead.model_validate(field)


@router.get("/projects/{project_id}/custom-fields", response_model=list[CustomFieldRead])
def list_custom_fields(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CustomFieldRead]:
    _ensure_project_access(db, project_id, current_user.id)

    fields = db.execute(
        select(CustomField)
        .where(CustomField.project_id == project_id)
        .options(selectinload(CustomField.options))
        .order_by(CustomField.created_at.asc())
    ).scalars().all()
    return [_serialize_field(field) for field in fields]


@router.post("/projects/{project_id}/custom-fields", response_model=CustomFieldRead, status_code=status.HTTP_201_CREATED)
def create_custom_field(
    project_id: int,
    payload: CustomFieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomFieldRead:
    project = _ensure_project_access(db, project_id, current_user.id)
    if payload.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project mismatch")

    field = CustomField(name=payload.name, type=payload.type, project_id=project_id)
    db.add(field)
    db.flush()

    if payload.options:
        for idx, option in enumerate(payload.options):
            db.add(
                CustomFieldOption(
                    custom_field_id=field.id,
                    value=option.value,
                    color=option.color,
                    position=option.position or idx,
                )
            )

    db.commit()
    field = _fetch_field(db, field.id)
    if field is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom field not found")
    return _serialize_field(field)


@router.delete("/custom-fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    field = _fetch_field(db, field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom field not found")
    _ensure_project_access(db, field.project_id, current_user.id)

    db.delete(field)
    db.commit()


@router.post("/tasks/{task_id}/custom-fields/{field_id}", response_model=CustomFieldRead)
def set_task_custom_field(
    task_id: int,
    field_id: int,
    payload: CustomFieldValuePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomFieldRead:
    task = _ensure_task_access(db, task_id, current_user.id)
    field = _fetch_field(db, field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom field not found")
    if field.project_id != task.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Custom field does not belong to task project")

    value = db.scalar(
        select(TaskCustomFieldValue).where(
            TaskCustomFieldValue.task_id == task_id,
            TaskCustomFieldValue.custom_field_id == field_id,
        )
    )
    if value is None:
        value = TaskCustomFieldValue(task_id=task_id, custom_field_id=field_id)
        db.add(value)

    expected_attr = {
        "text": "value_text",
        "number": "value_number",
        "date": "value_date",
        "dropdown": "value_text",
        "boolean": "value_boolean",
    }[field.type]
    provided_value = getattr(payload, expected_attr)
    if provided_value is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Value does not match field type")

    if field.type == "dropdown":
        valid_options = {option.value for option in field.options}
        if provided_value not in valid_options:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dropdown value not recognised")

    value.value_text = payload.value_text
    value.value_number = payload.value_number
    value.value_date = payload.value_date
    value.value_boolean = payload.value_boolean

    db.commit()

    field = db.execute(
        select(CustomField)
        .where(CustomField.id == field_id)
        .options(selectinload(CustomField.options))
    ).scalars().first()
    if field is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom field not found")
    return _serialize_field(field)


@router.delete("/tasks/{task_id}/custom-fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_task_custom_field(
    task_id: int,
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = _ensure_task_access(db, task_id, current_user.id)
    field = db.get(CustomField, field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom field not found")
    if field.project_id != task.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Custom field does not belong to task project")

    value = db.scalar(
        select(TaskCustomFieldValue).where(
            TaskCustomFieldValue.task_id == task_id,
            TaskCustomFieldValue.custom_field_id == field_id,
        )
    )
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Value not found")

    db.delete(value)
    db.commit()
