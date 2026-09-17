"""Project permissions — the SINGLE source of truth.

Object-level helpers (can_read_project / can_manage_project) and query-level
scopes (visible_project_ids_subquery / apply_project_read_scope) live here and
only here. Search, Project/Task/Experiment lists, Export, Dashboard and AI
Retrieval must all import from this module; duplicating these rules anywhere
else is a bug.

Rules:
- PI: reads/manages every non-deleted project.
- GUEST: reads nothing project-scoped.
- Everyone else: read = owner OR active member OR visibility = "lab"
  (EQUIPMENT_ADMIN deliberately NOT included — they see no research data).
- Manage = PI OR owner OR active member with role owner/manager.
- Tasks additionally follow the product rule that the assignee can always
  read their own tasks (expressed in SQL, never in Python loops).
"""

from sqlalchemy import Select, false as sa_false, select
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.project import Project, ProjectMember, Task
from app.models.user import User

TEACHING_STAFF_ROLES = (Role.PI, Role.TEACHER)
# roles that may read "visibility = lab" projects (equipment admin excluded)
LAB_VISIBLE_ROLES = (Role.TEACHER, Role.STUDENT)


# ---------- object level ----------


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
    if is_project_member(db, project.id, user.id) is not None:
        return True
    return project.visibility == "lab" and user.role in LAB_VISIBLE_ROLES


def can_manage_project(db: Session, user: User, project: Project) -> bool:
    if project.deleted_at is not None:
        return False
    if user.role == Role.PI:
        return True
    if project.owner_id == user.id:
        return True
    membership = is_project_member(db, project.id, user.id)
    return membership is not None and membership.project_role in ("owner", "manager")


def can_create_experiment(db: Session, user: User, project: Project) -> bool:
    """Creating records requires membership — lab visibility alone is not enough."""
    if user.role == Role.PI:
        return True
    if project.owner_id == user.id:
        return True
    return is_project_member(db, project.id, user.id) is not None


def ensure_project_visible(db: Session, user: User, project: Project) -> None:
    if not can_read_project(db, user, project):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="没有查看该项目的权限")


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
    if user.role == Role.GUEST:
        return stmt.where(sa_false())
    member_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user.id, ProjectMember.left_at.is_(None)
    )
    conditions = Project.owner_id == user.id
    conditions = conditions | Project.id.in_(member_ids)
    if user.role in LAB_VISIBLE_ROLES:
        conditions = conditions | (Project.visibility == "lab")
    return stmt.where(conditions)


def apply_project_read_scope(stmt: Select, user: User, project_column) -> Select:
    """Constrain `stmt` so `project_column` only refers to readable projects."""
    return stmt.where(project_column.in_(visible_project_ids_subquery(user)))


def visible_task_scope_conditions(user: User):
    """Conditions for readable tasks: own tasks OR tasks in readable projects."""
    return (Task.assignee_id == user.id) | Task.project_id.in_(
        visible_project_ids_subquery(user)
    )
