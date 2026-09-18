"""Project permissions — the SINGLE source of truth.

Visibility semantics (deliberately distinct tiers):

- private:         PI, owner, active member with owner/manager role
- project_members: PI, owner, any active member
- lab:             PI, owner, any active member, TEACHER, STUDENT

EQUIPMENT_ADMIN and GUEST are denied research data up front — membership,
ownership or assignee status never grants them access.

Object-level helpers (can_read_project / can_manage_project / ...) and
query-level scopes (visible_project_ids_subquery / apply_project_read_scope /
visible_task_scope_conditions) live here and only here.
"""

from sqlalchemy import Select, and_, select
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.project import Project, ProjectMember, Task
from app.models.user import User

TEACHING_STAFF_ROLES = (Role.PI, Role.TEACHER)
# roles allowed to browse lab-visible projects
LAB_VISIBLE_ROLES = (Role.TEACHER, Role.STUDENT)
# research data is flat-out denied for these roles, before any membership check
RESEARCH_DENIED_ROLES = (Role.EQUIPMENT_ADMIN, Role.GUEST)
_MANAGER_ROLES = ("owner", "manager")

_RESEARCH_DENIED = "当前角色无权访问科研项目数据"


def is_research_denied(user: User) -> bool:
    return user.role in RESEARCH_DENIED_ROLES


def is_project_member(
    db: Session, project_id: int, user_id: int
) -> ProjectMember | None:
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
    if is_research_denied(user):
        return False
    if user.role == Role.PI:
        return True
    if project.owner_id == user.id:
        return True
    membership = is_project_member(db, project.id, user.id)
    is_manager = membership is not None and membership.project_role in _MANAGER_ROLES
    if is_manager:
        return True
    if project.visibility == "lab":
        if membership is not None:
            return True
        return user.role in LAB_VISIBLE_ROLES
    if project.visibility == "project_members":
        return membership is not None
    return False  # private


def can_manage_project(db: Session, user: User, project: Project) -> bool:
    if project.deleted_at is not None:
        return False
    if is_research_denied(user):
        return False
    if user.role == Role.PI:
        return True
    if project.owner_id == user.id:
        return True
    membership = is_project_member(db, project.id, user.id)
    return membership is not None and membership.project_role in _MANAGER_ROLES


def can_create_experiment(db: Session, user: User, project: Project) -> bool:
    """Creating records requires membership — lab visibility alone is not enough."""
    if is_research_denied(user):
        return False
    if user.role == Role.PI:
        return True
    if project.owner_id == user.id:
        return True
    return is_project_member(db, project.id, user.id) is not None


def can_assign_task_to(db: Session, project: Project, assignee: User) -> bool:
    """Assignee must be an active user allowed to participate in research,
    and (on private/project_members projects) a project member."""
    if assignee.role in RESEARCH_DENIED_ROLES or assignee.status != "active":
        return False
    if project.visibility == "lab":
        return True
    return is_project_member(db, project.id, assignee.id) is not None


def ensure_project_visible(db: Session, user: User, project: Project) -> None:
    if not can_read_project(db, user, project):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=403,
            detail=_RESEARCH_DENIED
            if is_research_denied(user)
            else "没有查看该项目的权限",
        )


def ensure_project_manageable(db: Session, user: User, project: Project) -> None:
    if not can_manage_project(db, user, project):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="没有管理该项目的权限")


# ---------- query level ----------


def visible_project_ids_subquery(user: User) -> Select:
    """Subquery of non-deleted project ids `user` may read."""
    stmt = select(Project.id).where(Project.deleted_at.is_(None))
    if user.role == Role.PI:
        return stmt
    if is_research_denied(user):
        return stmt.where(sa_false())

    member_filter = (
        ProjectMember.user_id == user.id,
        ProjectMember.left_at.is_(None),
    )
    manager_ids = select(ProjectMember.project_id).where(
        *member_filter, ProjectMember.project_role.in_(_MANAGER_ROLES)
    )
    member_ids = select(ProjectMember.project_id).where(*member_filter)
    conditions = (Project.owner_id == user.id) | Project.id.in_(manager_ids)
    conditions = conditions | and_(
        Project.id.in_(member_ids),
        Project.visibility.in_(("project_members", "lab")),
    )
    if user.role in LAB_VISIBLE_ROLES:
        conditions = conditions | (Project.visibility == "lab")
    return stmt.where(conditions)


def apply_project_read_scope(stmt: Select, user: User, project_column) -> Select:
    """Constrain `stmt` so `project_column` only refers to readable projects."""
    return stmt.where(project_column.in_(visible_project_ids_subquery(user)))


def visible_task_scope_conditions(user: User):
    """Conditions for readable tasks: project readable AND project alive.

    The assignee branch only applies to users allowed to hold research tasks.
    """
    base = Task.project_id.in_(visible_project_ids_subquery(user))
    if is_research_denied(user):
        return base
    return base | (
        (Task.assignee_id == user.id)
        & Task.project_id.in_(select(Project.id).where(Project.deleted_at.is_(None)))
    )
