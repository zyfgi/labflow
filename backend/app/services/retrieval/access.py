"""Query-level permission scopes shared by Search, list APIs, exports and AI retrieval.

Rules (single source of truth — do NOT duplicate these conditions elsewhere):

- PI: reads every non-deleted project.
- GUEST: reads nothing project-scoped.
- Everyone else: owner OR active project member OR visibility = "lab".
- Tasks additionally follow the existing product rule that the assignee can
  always read their own task (expressed in SQL, not Python loops).
"""

from sqlalchemy import Select, false as sa_false, select
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.project import Project, ProjectMember, Task
from app.models.user import User

TEACHING_STAFF_ROLES = (Role.PI, Role.TEACHER)
LAB_VISIBLE_ROLES = (Role.TEACHER, Role.STUDENT, Role.EQUIPMENT_ADMIN)


def is_teaching_staff(user: User) -> bool:
    """PI/TEACHER: member-development data. EQUIPMENT_ADMIN is NOT included."""
    return user.role in TEACHING_STAFF_ROLES


def visible_project_ids_subquery(user: User) -> Select:
    """Subquery returning the ids of non-deleted projects `user` may read."""
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


def scoped_projects_stmt(user: User) -> Select:
    """Select over Project rows the user may read."""
    return select(Project).where(Project.id.in_(visible_project_ids_subquery(user)))


def scoped_tasks_stmt(user: User) -> Select:
    """Select over Task rows the user may read (project scope + own tasks)."""
    stmt = select(Task).where(
        Task.deleted_at.is_(None),
        (Task.assignee_id == user.id)
        | Task.project_id.in_(visible_project_ids_subquery(user)),
    )
    return stmt


def load_user(db: Session, user_id: int | None) -> User | None:
    if user_id is None:
        return None
    return db.get(User, user_id)
