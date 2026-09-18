"""WeChat miniprogram login and account binding.

Flow: wx.login -> code -> backend code2Session -> openid. The openid must be
bound to an existing LabFlow account (username + password + a one-time PI
binding code). Auto-registration is forbidden; the binding code is never
stored in plaintext after use and never appears in audit logs.
"""

import secrets
from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings as bootstrap
from app.core.deps import get_current_user, require_pi, write_audit_log
from app.core.responses import ok
from app.core.security import create_access_token, verify_password
from app.core.time import utcnow
from app.database import get_db
from app.models.user import User
from app.models.wechat import WeChatBindingCode
from app.schemas.base import StrictSchema
from app.services import runtime_settings
from app.services.notifications import notify

router = APIRouter(prefix="/wechat", tags=["wechat"])

_CODE_TTL_MINUTES = 30


class WeChatSessionRequest(StrictSchema):
    code: str = Field(min_length=1, max_length=200)


class WeChatBindRequest(StrictSchema):
    code: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)
    binding_code: str = Field(min_length=1, max_length=32)


class BindingCodeCreate(StrictSchema):
    remark: str | None = Field(default=None, max_length=200)
    ttl_minutes: int = Field(default=_CODE_TTL_MINUTES, ge=5, le=1440)


def _code2session(code: str) -> str:
    """Exchange a wx.login code for an openid. Without real appid/secret
    (development), a code of the form 'mock:<openid>' resolves directly."""
    if not bootstrap.WECHAT_APPID:
        if code.startswith("mock:"):
            return code[5:]
        raise HTTPException(
            status_code=503,
            detail="微信小程序未配置 WECHAT_APPID/WECHAT_SECRET（开发环境可用 mock:<openid>）",
        )
    resp = httpx.get(
        "https://api.weixin.qq.com/sns/jscode2session",
        params={
            "appid": bootstrap.WECHAT_APPID,
            "secret": bootstrap.WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    data = resp.json()
    openid = data.get("openid")
    if not openid:
        raise HTTPException(
            status_code=401,
            detail="微信登录失败：" + str(data.get("errmsg", "code 无效")),
        )
    return openid


def _require_miniprogram_enabled(db: Session) -> None:
    if not runtime_settings.effective(db).WECHAT_MINIPROGRAM_ENABLED:
        raise HTTPException(status_code=403, detail="微信小程序入口未启用")


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
    }


@router.post("/session")
def wechat_session(
    body: WeChatSessionRequest,
    db: Session = Depends(get_db),
) -> dict:
    """code2Session; returns a JWT directly when the openid is already bound."""
    _require_miniprogram_enabled(db)
    openid = _code2session(body.code)
    user = db.scalar(select(User).where(User.wechat_openid == openid))
    if user and user.status == "active":
        user.last_login_at = utcnow()
        db.commit()
        return ok(
            {
                "openid": openid,
                "bound": True,
                "token": create_access_token(str(user.id), {"role": user.role}),
                "user": _user_payload(user),
            }
        )
    return ok({"openid": openid, "bound": False, "token": None, "user": None})


@router.post("/bind")
def wechat_bind(
    body: WeChatBindRequest,
    db: Session = Depends(get_db),
) -> dict:
    """First-time bind: existing LabFlow credentials + one-time PI code."""
    _require_miniprogram_enabled(db)
    openid = _code2session(body.code)
    user = db.scalar(select(User).where(User.wechat_openid == openid))
    if user:
        raise HTTPException(status_code=409, detail="该微信已绑定账号，无需重复绑定")
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已停用")
    if user.wechat_openid:
        raise HTTPException(status_code=409, detail="该账号已绑定其他微信，请先解绑")

    binding_code = db.scalar(
        select(WeChatBindingCode).where(WeChatBindingCode.code == body.binding_code)
    )
    now = utcnow()
    if (
        binding_code is None
        or binding_code.used_at is not None
        or binding_code.expires_at < now
    ):
        raise HTTPException(
            status_code=403, detail="绑定码无效或已过期，请联系 PI 获取"
        )

    user.wechat_openid = openid
    user.wechat_bound_at = now
    user.last_login_at = now
    binding_code.used_at = now
    binding_code.used_by = user.id
    write_audit_log(db, user, "bind_wechat", "user", user.id)
    notify(
        db,
        [binding_code.created_by, user.id],
        "wechat_bound",
        "微信绑定成功",
        f"账号 {user.username} 已绑定微信",
        "user",
        user.id,
    )
    db.commit()
    return ok(
        {
            "token": create_access_token(str(user.id), {"role": user.role}),
            "user": _user_payload(user),
        },
        message="绑定成功",
    )


@router.delete("/bind")
def wechat_unbind(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Self-service unbind (client confirms first); immediate + audited."""
    if not user.wechat_openid:
        raise HTTPException(status_code=400, detail="当前账号未绑定微信")
    user.wechat_openid = None
    user.wechat_bound_at = None
    write_audit_log(db, user, "unbind_wechat", "user", user.id)
    notify(
        db,
        [user.id],
        "wechat_unbound",
        "微信已解绑",
        "账号已解除微信绑定",
        "user",
        user.id,
    )
    db.commit()
    return ok(message="已解除微信绑定")


@router.get("/binding-codes")
def list_binding_codes(
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    now = utcnow()
    rows = db.scalars(
        select(WeChatBindingCode).order_by(WeChatBindingCode.id.desc()).limit(50)
    ).all()
    return ok(
        [
            {
                "id": c.id,
                "code": c.code,
                "remark": c.remark,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "expires_at": c.expires_at.isoformat(),
                "state": (
                    "used"
                    if c.used_at
                    else ("expired" if c.expires_at < now else "valid")
                ),
            }
            for c in rows
        ]
    )


@router.post("/binding-codes", status_code=201)
def create_binding_code(
    body: BindingCodeCreate,
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    code = secrets.token_hex(4).upper()  # 8 hex chars, one-time and short-lived
    record = WeChatBindingCode(
        code=code,
        created_by=user.id,
        expires_at=utcnow() + timedelta(minutes=body.ttl_minutes),
        remark=body.remark,
    )
    db.add(record)
    db.flush()
    write_audit_log(
        db, user, "create_wechat_binding_code", "wechat_binding_code", record.id
    )
    db.commit()
    return ok(
        {
            "code": code,
            "expires_at": record.expires_at.isoformat(),
            "remark": record.remark,
        },
        message="绑定码已生成，请当面交付给成员本人",
    )
