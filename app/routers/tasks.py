"""Task endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import UserWorkspace, Workspace
from app.schemas.task import PaginatedTasks, PaginationMeta, TaskCreate, TaskRead, TaskUpdate

router = APIRouter()


def _assert_workspace_access(db: Session, user: User, workspace_id: int) -> None:
    membership = db.get(UserWorkspace, (user.id, workspace_id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of workspace")


@router.get("", response_model=PaginatedTasks)
def list_tasks(
    workspace_id: int = Query(..., description="Workspace identifier"),
    project_id: int | None = Query(None),
    assignee: str | None = Query(None, description='Filter by assignee. Use "me" for the current user.'),
    completed: bool | None = Query(None),
    completed_since: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedTasks:
    _assert_workspace_access(db, current_user, workspace_id)

    base_filters = [Project.workspace_id == workspace_id]
    if project_id is not None:
        base_filters.append(Task.project_id == project_id)

    if assignee:
        if assignee == "me":
            base_filters.append(Task.assignee_id == current_user.id)
        else:
            try:
                assignee_id = int(assignee)
            except ValueError as exc:  # pragma: no cover - validation guard
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid assignee filter") from exc
            base_filters.append(Task.assignee_id == assignee_id)

    if completed is not None:
        condition = Task.completed_at.isnot(None) if completed else Task.completed_at.is_(None)
        base_filters.append(condition)

    if completed_since is not None:
        base_filters.append(Task.completed_at.isnot(None))
        base_filters.append(Task.completed_at >= completed_since)

    query = (
        select(Task)
        .join(Project)
        .where(and_(*base_filters))
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.parent),
            selectinload(Task.project)
            .selectinload(Project.workspace)
            .selectinload(Workspace.owner),
        )
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    tasks = db.execute(query).scalars().unique().all()

    count_query = (
        select(func.count())
        .select_from(select(Task.id).join(Project).where(and_(*base_filters)).subquery())
    )
    total = db.scalar(count_query) or 0

    return PaginatedTasks(
        data=[TaskRead.model_validate(task) for task in tasks],
        pagination=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_access(db, current_user, project.workspace_id)

    task_data = payload.model_dump(exclude={"completed"})
    task_data["creator_id"] = current_user.id

    task = Task(**task_data)
    if payload.completed:
        task.completed_at = datetime.now(timezone.utc)

    db.add(task)
    db.commit()
    return _serialize_task(db, task.id)


@router.get("/{task_id}", response_model=TaskRead)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = _resolve_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    project = task.project
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_access(db, current_user, project.workspace_id)
    return TaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = _resolve_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    project = task.project
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_access(db, current_user, project.workspace_id)

    update_data = payload.model_dump(exclude_none=True)
    completed_flag = update_data.pop("completed", None)

    for field, value in update_data.items():
        setattr(task, field, value)

    if completed_flag is not None:
        task.completed_at = datetime.now(timezone.utc) if completed_flag else None

    db.commit()
    return _serialize_task(db, task.id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = _resolve_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    project = task.project
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_access(db, current_user, project.workspace_id)

    db.delete(task)
    db.commit()


def _resolve_task(db: Session, task_id: int) -> Task | None:
    return db.scalar(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.parent),
            selectinload(Task.project)
            .selectinload(Project.workspace)
            .selectinload(Workspace.owner),
        )
    )


def _serialize_task(db: Session, task_id: int) -> TaskRead:
    task = _resolve_task(db, task_id)
    if task is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskRead.model_validate(task)
