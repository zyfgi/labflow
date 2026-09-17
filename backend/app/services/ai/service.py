"""AI chat orchestration: rate limit → (optional) LLM planner → permission-
scoped local retrieval → bounded context → provider call → persistence +
audit. Every turn re-runs retrieval with the *current* user permissions.
"""

import json
import logging
import re
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import write_audit_log
from app.models.ai import AIConversation, AIMessage, AIRequestLog
from app.models.user import User
from app.services.ai.context_builder import build_context, source_label
from app.services.ai.errors import AIConfigError, AIError, AIDisabledError
from app.services.ai.prompts import (
    NO_RESULT_ANSWER,
    PLANNER_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    planner_user_prompt,
)
from app.services.ai.provider import LLMProvider, build_provider
from app.services.ai.rate_limit import limiter
from app.services.ai.schemas import AISource
from app.services.retrieval.engine import retrieve
from app.services.retrieval.intent_parser import parse_query
from app.services.retrieval.types import RetrievalPlan

logger = logging.getLogger("labflow.ai")

HISTORY_MESSAGE_LIMIT = 8


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply (tolerates fences)."""
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in planner reply")
    return json.loads(match.group(0))


async def _llm_plan(provider: LLMProvider, question: str) -> RetrievalPlan | None:
    """First LLM call: question only — no LabFlow data ever leaves here.

    Any failure falls back to the rule-based parser (never fails the request).
    """
    try:
        resp = await provider.chat(
            [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": planner_user_prompt(question)},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        data = _extract_json(resp.content)
        allowed = {k: data[k] for k in RetrievalPlan.model_fields if k in data}
        return RetrievalPlan.model_validate(allowed)
    except Exception as e:
        logger.info("query planner fallback: %s", e.__class__.__name__)
        return None


def _get_or_create_conversation(
    db: Session, user: User, conversation_id: int | None, message: str
) -> AIConversation:
    if conversation_id:
        conv = db.get(AIConversation, conversation_id)
        if conv is None or conv.user_id != user.id or conv.deleted_at is not None:
            raise AIError("conversation_not_found", friendly="对话不存在")
        return conv
    conv = AIConversation(user_id=user.id, title=message[:40] or "新对话")
    db.add(conv)
    db.flush()
    return conv


def _recent_history(conv: AIConversation) -> list[dict]:
    """Recent turns only; each new turn re-retrieves fresh data anyway."""
    msgs = sorted(conv.messages, key=lambda m: m.id)[-HISTORY_MESSAGE_LIMIT:]
    return [{"role": m.role, "content": m.content} for m in msgs if m.role in ("user", "assistant")]


async def ai_chat(
    db: Session,
    user: User,
    message: str,
    conversation_id: int | None = None,
    provider: LLMProvider | None = None,
) -> dict:
    if not settings.AI_ENABLED and provider is None:
        raise AIDisabledError("AI_ENABLED is false")
    limiter.check(user.id)

    started = time.perf_counter()
    own_provider = provider is None
    provider = provider or build_provider()  # AIConfigError if misconfigured

    conversation = _get_or_create_conversation(db, user, conversation_id, message)
    db.add(AIMessage(conversation_id=conversation.id, role="user", content=message))
    db.flush()

    retrieval_count = 0
    status = "success"
    error_code = None
    try:
        plan: RetrievalPlan | None = None
        if settings.AI_QUERY_PLANNER_ENABLED:
            plan = await _llm_plan(provider, message)
        if plan is None:
            plan = parse_query(message)

        _plan, hits = retrieve(
            db, user, message, plan=plan, limit=settings.AI_MAX_RETRIEVAL_HITS
        )
        retrieval_count = len(hits)

        if not hits:
            answer = NO_RESULT_ANSWER
            provider_model = getattr(provider, "model", None)
            input_tokens = output_tokens = None
        else:
            context = build_context(message, hits)
            chat_messages = (
                [{"role": "system", "content": SYSTEM_PROMPT}]
                + _recent_history(conversation)
                + [{"role": "user", "content": f"Question: {message}\n\n{context}"}]
            )
            resp = await provider.chat(chat_messages)
            answer = resp.content
            provider_model = resp.model
            input_tokens, output_tokens = resp.input_tokens, resp.output_tokens

        sources = [
            AISource(type=h.source_type, id=h.source_id, title=h.title, url=h.url).model_dump()
            for h in hits
        ]
        db.add(
            AIMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
                sources_json=sources,
                model=provider_model,
            )
        )
    except AIError as e:
        status = "error"
        error_code = e.code
        latency_ms = int((time.perf_counter() - started) * 1000)
        db.add(
            AIRequestLog(
                user_id=user.id,
                conversation_id=conversation.id,
                provider="openai_compatible",
                model=getattr(provider, "model", None),
                retrieval_count=retrieval_count,
                latency_ms=latency_ms,
                status=status,
                error_code=error_code,
            )
        )
        write_audit_log(
            db, user, "ai_provider_error", "ai_conversation", conversation.id,
            {"error_code": e.code, "latency_ms": latency_ms},
        )
        db.commit()
        raise
    finally:
        if own_provider and hasattr(provider, "aclose"):
            try:
                await provider.aclose()
            except Exception:
                pass

    latency_ms = int((time.perf_counter() - started) * 1000)
    db.add(
        AIRequestLog(
            user_id=user.id,
            conversation_id=conversation.id,
            provider="openai_compatible",
            model=getattr(provider, "model", None),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            retrieval_count=retrieval_count,
            latency_ms=latency_ms,
            status=status,
        )
    )
    write_audit_log(
        db, user, "ai_chat", "ai_conversation", conversation.id,
        {
            "model": provider_model,
            "retrieval_count": retrieval_count,
            "latency_ms": latency_ms,
            "status": status,
            # query text stored only when explicitly configured
            **({"query": message[:200]} if settings.AI_AUDIT_STORE_QUERY else {}),
        },
    )
    db.commit()
    return {
        "conversation_id": conversation.id,
        "answer": answer,
        "sources": sources,
        "model": provider_model,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "source_labels": [source_label(h) for h in hits],
    }
