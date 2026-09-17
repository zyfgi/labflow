"""AI assistant API: chat, conversations, retrieval debug endpoint."""

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, write_audit_log
from app.core.responses import ok, paged
from app.database import get_db
from app.models.ai import AIConversation, AIMessage
from app.models.user import User
from app.services.ai.errors import (
    AIError,
    provider_status,
)
from app.services.ai.schemas import (
    AIChatRequest,
    AIConversationCreate,
    AIRetrieveRequest,
)
from app.services.ai.service import ai_chat
from app.services.retrieval.engine import retrieve

router = APIRouter(prefix="/ai", tags=["ai"])

_STATUS_TO_HTTP = {
    "AI_DISABLED": 503,
    "AI_CONFIG_ERROR": 500,
    "AI_PROVIDER_TIMEOUT": 504,
    "AI_PROVIDER_AUTH_ERROR": 502,
    "AI_PROVIDER_RATE_LIMIT": 429,
    "AI_RATE_LIMITED": 429,
    "AI_PROVIDER_ERROR": 502,
    "AI_RESPONSE_INVALID": 502,
}


def _ai_http_error(e: AIError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_TO_HTTP.get(e.code, 502),
        detail={"code": e.code, "message": e.friendly},
    )


@router.post("/chat")
async def chat(
    body: AIChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = await ai_chat(db, user, body.message.strip(), body.conversation_id)
    except AIError as e:
        raise _ai_http_error(e)
    return ok(result)


@router.get("/status")
def ai_status(user: User = Depends(get_current_user)) -> dict:
    return ok(provider_status())


@router.post("/retrieve")
def retrieve_debug(
    body: AIRetrieveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieval-only debug endpoint: no LLM call.

    Development: open to authenticated users. Production: PI only and only
    when AI_DEBUG_RETRIEVAL=true.
    """
    allowed = settings.effective_ai_debug_retrieval or user.role == "PI"
    if not allowed:
        raise HTTPException(status_code=403, detail="检索调试接口未开放")
    started = time.perf_counter()
    plan, hits = retrieve(
        db, user, body.query.strip(), source_types=body.source_types, limit=body.limit
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    write_audit_log(
        db, user, "ai_retrieve", "ai_debug", None,
        {"retrieval_count": len(hits), "latency_ms": latency_ms},
    )
    db.commit()
    return ok(
        {
            "plan": plan.model_dump(),
            "hits": [h.to_dict() for h in hits],
            "latency_ms": latency_ms,
        }
    )


# ---------- conversations (strictly owned by the current user) ----------


def _own_conversation(db: Session, user: User, conversation_id: int) -> AIConversation:
    conv = db.get(AIConversation, conversation_id)
    if conv is None or conv.user_id != user.id or conv.deleted_at is not None:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


@router.get("/conversations")
def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(AIConversation).where(
        AIConversation.user_id == user.id, AIConversation.deleted_at.is_(None)
    )
    from sqlalchemy import func

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AIConversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return paged(
        [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in rows],
        total,
        page,
        page_size,
    )


@router.post("/conversations", status_code=201)
def create_conversation(
    body: AIConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conv = AIConversation(user_id=user.id, title=(body.title or "新对话")[:200])
    db.add(conv)
    db.commit()
    return ok({"id": conv.id, "title": conv.title}, message="对话已创建")


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conv = _own_conversation(db, user, conversation_id)
    messages = db.scalars(
        select(AIMessage).where(AIMessage.conversation_id == conv.id).order_by(AIMessage.id)
    ).all()
    return ok(
        {
            "id": conv.id,
            "title": conv.title,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "sources": m.sources_json or [],
                    "model": m.model,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conv = _own_conversation(db, user, conversation_id)
    from app.models.base import utcnow

    conv.deleted_at = utcnow()
    db.commit()
    return ok(message="对话已删除")
