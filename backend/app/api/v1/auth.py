from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import client_ip, get_current_user, write_audit_log
from app.core.responses import ok
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.enums import UserStatus
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, LoginRequest, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    stmt = select(User).where((User.username == body.username) | (User.email == body.username))
    user = db.scalar(stmt)
    # Generic failure message: do not reveal whether the username exists.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用，请联系管理员")

    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    write_audit_log(db, user, "login", "user", user.id, ip_address=client_ip(request))
    db.commit()

    token = create_access_token(str(user.id), {"role": user.role})
    return TokenOut(
        access_token=token,
        must_change_password=user.must_change_password,
        user=UserOut.model_validate(user),
    ).model_dump()


@router.post("/logout")
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    write_audit_log(db, user, "logout", "user", user.id, ip_address=client_ip(request))
    db.commit()
    return ok(message="已退出登录")


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return ok(UserOut.model_validate(user).model_dump())


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码不正确")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    write_audit_log(db, user, "change_password", "user", user.id)
    db.commit()
    return ok(message="密码修改成功")
