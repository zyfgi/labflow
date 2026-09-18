from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.enums import Role
from app.models.system import AuditLog
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="未登录或登录已过期",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if not token:
        raise CREDENTIALS_ERROR
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise CREDENTIALS_ERROR
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise CREDENTIALS_ERROR
    user = db.get(User, user_id)
    if user is None or user.status != "active":
        raise CREDENTIALS_ERROR
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="没有执行该操作的权限"
            )
        return user

    return dependency


require_pi = require_roles(Role.PI)
require_teacher_or_pi = require_roles(Role.PI, Role.TEACHER)


def write_audit_log(
    db: Session,
    user: User | None,
    action: str,
    resource_type: str | None = None,
    resource_id: Any = None,
    detail: dict | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            detail_json=detail,
            ip_address=ip_address,
        )
    )


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
