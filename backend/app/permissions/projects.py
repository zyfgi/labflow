"""Project-level resource permissions: role + ownership + membership + visibility."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.project import Project, ProjectMember
from app.models.user import User


def is_project_member(db: Session, project_id: int, user_id: int) -> ProjectMember | None:
    return db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.left_at.is_(None),
        )
    )


def can_read_project(db: Session, user: User, project: Project) -> bool:
    if project.deleted_at is not None:
        return False
    if user.role == Role.PI:
        return True
    if user.role == Role.GUEST:
        return False
    if project.owner_id == user.id:
        return True
    membership = is_project_member(db, project.id, user.id)
    if membership is not None:
        return True
    if project.visibility == "lab" and user.role in (Role.TEACHER, Role.STUDENT, Role.EQUIPMENT_ADMIN):
        return True
    return False


def can_manage_project(db: Session, user: User, project: Project) -> bool:
    if project.deleted_at is not None:
        return False
    if user.role == Role.PI:
        return True
    if project.owner_id == user.id:
        return True
    membership = is_project_member(db, project.id, user.id)
    if membership is not None and membership.project_role in ("owner", "manager"):
        return True
    return False


def visible_project_ids(db: Session, user: User) -> list[int] | None:
    """None means 'no extra filter' (user can see everything)."""
    if user.role == Role.PI:
        return None
    member_ids = list(
        db.scalars(
            select(ProjectMember.project_id).where(
                ProjectMember.user_id == user.id, ProjectMember.left_at.is_(None)
            )
        )
    )
    return member_ids  # refined by visibility in the list query


def ensure_project_visible(db: Session, user: User, project: Project) -> None:
    if not can_read_project(db, user, project):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="没有查看该项目的权限")


def ensure_project_manageable(db: Session, user: User, project: Project) -> None:
    if not can_manage_project(db, user, project):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="没有管理该项目的权限")
