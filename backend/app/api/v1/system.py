"""System settings API (PI only): view + edit runtime config, test AI connection."""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_pi, write_audit_log
from app.core.responses import ok
from app.database import get_db
from app.models.user import User
from app.services import runtime_settings
from app.services.ai.errors import AIError
from app.services.ai.provider import OpenAICompatibleProvider
from app.services.runtime_settings import RuntimeSettingsUpdate

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/settings")
def get_settings(
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    return ok(runtime_settings.to_admin_view(db))


@router.patch("/settings")
def update_settings(
    body: RuntimeSettingsUpdate,
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    try:
        runtime_settings.update_runtime(db, body, updated_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    write_audit_log(
        db,
        user,
        "update_settings",
        "system_settings",
        1,
        {
            "fields": [
                k for k in body.model_dump(exclude_unset=True) if k != "AI_API_KEY"
            ]
        },
    )
    db.commit()
    return ok(runtime_settings.to_admin_view(db), message="设置已保存")


@router.post("/settings/ai/test")
async def test_ai_connection(
    user: User = Depends(require_pi),
    db: Session = Depends(get_db),
) -> dict:
    """Dial the configured provider with a 1-token prompt; never returns the
    provider response body or the key."""
    cfg = runtime_settings.effective(db)
    if not cfg.AI_ENABLED:
        raise HTTPException(status_code=400, detail="AI 未启用")
    api_key = runtime_settings.get_ai_api_key(db)
    if not (cfg.AI_BASE_URL and api_key and cfg.AI_MODEL):
        raise HTTPException(status_code=400, detail="AI 配置不完整")
    provider = OpenAICompatibleProvider(
        base_url=cfg.AI_BASE_URL,
        api_key=api_key,
        model=cfg.AI_MODEL,
        timeout_seconds=min(cfg.AI_TIMEOUT_SECONDS, 30),
    )
    started = time.perf_counter()
    try:
        resp = await provider.chat(
            [{"role": "user", "content": "ping"}], temperature=0.0, max_tokens=1
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ok(
            {
                "ok": True,
                "model": resp.model,
                "latency_ms": latency_ms,
            }
        )
    except AIError as e:
        return ok({"ok": False, "code": e.code, "message": e.friendly})
