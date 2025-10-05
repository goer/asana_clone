"""Section endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.section import Section
from app.models.user import User
from app.models.workspace import UserWorkspace
from app.schemas.section import SectionCreate, SectionRead, SectionUpdate

router = APIRouter()


def _assert_workspace_membership(db: Session, user: User, project: Project) -> None:
    membership = db.get(UserWorkspace, (user.id, project.workspace_id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of workspace")


@router.get("", response_model=list[SectionRead])
def list_sections(
    project_id: int = Query(..., description="Project identifier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SectionRead]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_membership(db, current_user, project)

    sections = db.scalars(select(Section).where(Section.project_id == project_id)).all()
    return [SectionRead.model_validate(section) for section in sections]


@router.post("", response_model=SectionRead, status_code=status.HTTP_201_CREATED)
def create_section(
    payload: SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SectionRead:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_membership(db, current_user, project)

    section = Section(**payload.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return SectionRead.model_validate(section)


@router.patch("/{section_id}", response_model=SectionRead)
def update_section(
    section_id: int,
    payload: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SectionRead:
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    project = db.get(Project, section.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_membership(db, current_user, project)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(section, field, value)

    db.commit()
    db.refresh(section)
    return SectionRead.model_validate(section)


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    project = db.get(Project, section.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _assert_workspace_membership(db, current_user, project)

    db.delete(section)
    db.commit()
