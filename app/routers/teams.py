"""Team management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user
from app.db.session import get_db
from app.models.team import Team, UserTeam
from app.models.user import User
from app.models.workspace import UserWorkspace
from app.schemas.team import TeamCreate, TeamMemberUpdate, TeamRead
from app.schemas.user import UserRead

router = APIRouter()


def _ensure_workspace_membership(db: Session, workspace_id: int, user_id: int) -> None:
    if db.get(UserWorkspace, (user_id, workspace_id)) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of workspace")


def _serialize_team(team: Team) -> TeamRead:
    members = [UserRead.model_validate(membership.user) for membership in team.memberships if membership.user]
    base = TeamRead.model_validate(team)
    return base.model_copy(update={"members": members})


@router.get("", response_model=list[TeamRead])
def list_teams(
    workspace_id: int = Query(..., description="Workspace identifier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TeamRead]:
    _ensure_workspace_membership(db, workspace_id, current_user.id)

    teams = db.execute(
        select(Team)
        .where(Team.workspace_id == workspace_id)
        .options(selectinload(Team.memberships).selectinload(UserTeam.user))
        .order_by(Team.created_at.asc())
    ).scalars().all()
    return [_serialize_team(team) for team in teams]


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamRead:
    _ensure_workspace_membership(db, payload.workspace_id, current_user.id)

    team = Team(**payload.model_dump())
    db.add(team)
    db.flush()

    membership = UserTeam(user_id=current_user.id, team_id=team.id)
    db.merge(membership)
    db.commit()
    team = db.execute(
        select(Team)
        .where(Team.id == team.id)
        .options(selectinload(Team.memberships).selectinload(UserTeam.user))
    ).scalars().first()
    if team is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return _serialize_team(team)


@router.post("/{team_id}/members", response_model=TeamRead)
def add_team_member(
    team_id: int,
    payload: TeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamRead:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    _ensure_workspace_membership(db, team.workspace_id, current_user.id)
    _ensure_workspace_membership(db, team.workspace_id, payload.user_id)

    db.merge(UserTeam(user_id=payload.user_id, team_id=team_id))
    db.commit()

    team = db.execute(
        select(Team)
        .where(Team.id == team_id)
        .options(selectinload(Team.memberships).selectinload(UserTeam.user))
    ).scalars().first()
    if team is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return _serialize_team(team)


@router.delete("/{team_id}/members/{user_id}", response_model=TeamRead)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamRead:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    _ensure_workspace_membership(db, team.workspace_id, current_user.id)

    membership = db.get(UserTeam, (user_id, team_id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    db.delete(membership)
    db.commit()

    team = db.execute(
        select(Team)
        .where(Team.id == team_id)
        .options(selectinload(Team.memberships).selectinload(UserTeam.user))
    ).scalars().first()
    if team is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return _serialize_team(team)
