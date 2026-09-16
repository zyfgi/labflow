from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_pi, require_teacher_or_pi, write_audit_log
from app.core.responses import ok, paged
from app.core.security import hash_password
from app.database import get_db
from app.models.enums import ALL_ROLES, Role
from app.models.user import User
from app.schemas.user import UserCreate, UserOption, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    user: User = Depends(require_teacher_or_pi),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if status:
        stmt = stmt.where(User.status == status)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(or_(User.username.ilike(kw), User.name.ilike(kw), User.email.ilike(kw)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return paged([UserOut.model_validate(u).model_dump() for u in rows], total, page, page_size)


@router.get("/options")
def user_options(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    rows = db.scalars(
        select(User).where(User.status == "active").order_by(User.name).limit(500)
    ).all()
    return ok([UserOption.model_validate(u).model_dump() for u in rows])


@router.post("", status_code=201)
def create_user(
    body: UserCreate,
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    if body.role not in ALL_ROLES:
        raise HTTPException(status_code=400, detail="无效的角色")
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status_code=409, detail="邮箱已被使用")

    new_user = User(
        username=body.username,
        name=body.name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        status=body.status,
        password_hash=hash_password(body.password),
    )
    db.add(new_user)
    db.flush()
    write_audit_log(db, user, "create_user", "user", new_user.id, {"username": new_user.username})
    db.commit()
    return ok(UserOut.model_validate(new_user).model_dump(), message="用户创建成功")


@router.get("/{user_id}")
def get_user(
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role not in (Role.PI, Role.TEACHER) and user.id != user_id:
        raise HTTPException(status_code=403, detail="没有查看该用户的权限")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ok(UserOut.model_validate(target).model_dump())


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdate,
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = body.model_dump(exclude_unset=True)

    if "email" in data and data["email"] != target.email:
        if db.scalar(select(User).where(User.email == data["email"])):
            raise HTTPException(status_code=409, detail="邮箱已被使用")
    if "role" in data and data["role"]:
        if data["role"] not in ALL_ROLES:
            raise HTTPException(status_code=400, detail="无效的角色")
        if data["role"] != target.role:
            write_audit_log(
                db, user, "change_role", "user", target.id,
                {"username": target.username, "from": target.role, "to": data["role"]},
            )
    if "password" in data and data["password"]:
        target.password_hash = hash_password(data.pop("password"))
        target.must_change_password = True
    if "status" in data and data["status"] not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="无效的状态")

    for field, value in data.items():
        if value is not None or field in ("phone", "avatar_url"):
            setattr(target, field, value)
    write_audit_log(db, user, "update_user", "user", target.id, {"fields": list(data.keys())})
    db.commit()
    return ok(UserOut.model_validate(target).model_dump(), message="用户更新成功")
