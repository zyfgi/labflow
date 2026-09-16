"""Project-level resource permission helpers (RBAC + resource ownership)."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.user import MemberProfile, User

STAFF_ROLES = (Role.PI, Role.TEACHER, Role.EQUIPMENT_ADMIN)


def get_member_profile(db: Session, user: User) -> MemberProfile | None:
    return db.get(MemberProfile, user.member_profile.id) if user.member_profile else None


def require_member_profile(user: User) -> MemberProfile:
    if not user.member_profile:
        raise HTTPException(status_code=400, detail="当前用户没有成员档案")
    return user.member_profile


def can_view_member(user: User, member: MemberProfile) -> bool:
    if user.role in STAFF_ROLES:
        return True
    return user.member_profile is not None and user.member_profile.id == member.id


def ensure_can_view_member(user: User, member: MemberProfile) -> None:
    if not can_view_member(user, member):
        raise HTTPException(status_code=403, detail="没有查看该成员的权限")


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES
