"""Project-level resource permission helpers (RBAC + resource ownership).

Member-development data (member profiles, learning plans, skills, weekly
reports, research progress) is restricted to PI / TEACHER. The equipment
admin role only manages equipment-domain endpoints; for display names it
receives bare `user_id`/`name` via existing joins, never full profiles.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.user import MemberProfile, User

# roles allowed to see member-development data
TEACHING_STAFF_ROLES = (Role.PI, Role.TEACHER)
# legacy alias used across modules; EQUIPMENT_ADMIN intentionally excluded
STAFF_ROLES = TEACHING_STAFF_ROLES


def get_member_profile(db: Session, user: User) -> MemberProfile | None:
    return (
        db.get(MemberProfile, user.member_profile.id) if user.member_profile else None
    )


def require_member_profile(user: User) -> MemberProfile:
    if not user.member_profile:
        raise HTTPException(status_code=400, detail="当前用户没有成员档案")
    return user.member_profile


def can_view_member(user: User, member: MemberProfile) -> bool:
    if user.role in TEACHING_STAFF_ROLES:
        return True
    return user.member_profile is not None and user.member_profile.id == member.id


def ensure_can_view_member(user: User, member: MemberProfile) -> None:
    if not can_view_member(user, member):
        raise HTTPException(status_code=403, detail="没有查看该成员的权限")


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def is_teaching_staff(user: User) -> bool:
    return user.role in TEACHING_STAFF_ROLES
