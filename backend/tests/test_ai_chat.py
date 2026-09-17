"""AI chat / conversation API tests (FakeLLMProvider, no real API)."""

import pytest

from app.core.config import settings
from app.services.ai.errors import AIProviderTimeoutError
from app.services.ai.provider import FakeLLMProvider
from tests.conftest import auth_headers


@pytest.fixture()
def ai_env(monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    fake = FakeLLMProvider(response="根据检索到的任务记录，回答内容……")
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda: fake)
    return fake


def _setup_project_with_task(client, db, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "聊天测试项目", "code": f"CHAT-{student.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "整理数据", "assignee_id": student.id},
        headers=auth_headers(pi),
    )
    return project_id


def test_chat_success_with_sources(client, db, pi, student, ai_env):
    _setup_project_with_task(client, db, pi, student)
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "我有哪些未完成的任务？"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["conversation_id"] > 0
    assert data["answer"]
    assert isinstance(data["sources"], list)
    assert any(s["type"] == "task" and s["url"] == f"/tasks/{s['id']}" for s in data["sources"])
    assert data["usage"]["input_tokens"] is not None
    # provider received system prompt + bounded context
    chat_call = ai_env.calls[-1]
    assert chat_call.messages[0]["role"] == "system"
    assert "untrusted" in chat_call.messages[0]["content"].lower()


def test_chat_disabled_returns_ai_disabled(client, db, student, monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "你好"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "AI_DISABLED"


def test_chat_provider_timeout_mapped(client, db, pi, student, monkeypatch):
    _setup_project_with_task(client, db, pi, student)
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    fake = FakeLLMProvider(error=AIProviderTimeoutError("simulated"))
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda: fake)
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "我有哪些未完成的任务？"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 504
    body = resp.json()["detail"]
    assert body["code"] == "AI_PROVIDER_TIMEOUT"
    assert "simulated" not in body["message"]  # internal detail never leaks
    assert "sk-" not in str(resp.json())


def test_chat_no_results_returns_canned_answer_without_llm(client, db, student, ai_env):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "完全不存在的内容XYZQM"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "没有找到足够信息" in data["answer"]
    assert data["sources"] == []
    # no LLM call at all when retrieval found nothing
    assert len(ai_env.calls) == 0


def test_conversation_history_and_ownership(client, db, pi, student, student_b, ai_env):
    _setup_project_with_task(client, db, pi, student)
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "我有哪些未完成的任务？"},
        headers=auth_headers(student),
    )
    conversation_id = resp.json()["data"]["conversation_id"]

    # owner sees messages
    resp = client.get(
        f"/api/v1/ai/conversations/{conversation_id}", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    messages = resp.json()["data"]["messages"]
    assert messages[0]["role"] == "user"
    assert messages[-1]["role"] == "assistant"

    # student B cannot read A's conversation (even PI cannot — private)
    resp = client.get(
        f"/api/v1/ai/conversations/{conversation_id}", headers=auth_headers(student_b)
    )
    assert resp.status_code == 404
    resp = client.get(
        f"/api/v1/ai/conversations/{conversation_id}", headers=auth_headers(pi)
    )
    assert resp.status_code == 404

    # multi-turn keeps the same conversation and re-retrieves each turn
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "那这些任务里哪个最紧急？", "conversation_id": conversation_id},
        headers=auth_headers(student),
    )
    assert resp.json()["data"]["conversation_id"] == conversation_id

    # list only own conversations
    resp = client.get("/api/v1/ai/conversations", headers=auth_headers(student_b))
    ids = [c["id"] for c in resp.json()["data"]["items"]]
    assert conversation_id not in ids

    # delete own conversation; afterwards inaccessible
    resp = client.delete(
        f"/api/v1/ai/conversations/{conversation_id}", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    resp = client.get(
        f"/api/v1/ai/conversations/{conversation_id}", headers=auth_headers(student)
    )
    assert resp.status_code == 404


def test_rate_limit_blocks_flood(client, db, student, monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_PER_MINUTE", 2)
    from app.services.ai.rate_limit import limiter

    limiter._windows.pop(student.id, None)
    fake = FakeLLMProvider()
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda: fake)
    for _ in range(2):
        resp = client.post(
            "/api/v1/ai/chat", json={"message": "最近有什么任务"}, headers=auth_headers(student)
        )
        assert resp.status_code == 200
    resp = client.post(
        "/api/v1/ai/chat", json={"message": "再来一条"}, headers=auth_headers(student)
    )
    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "AI_RATE_LIMITED"
    limiter._windows.pop(student.id, None)


def test_chat_input_validation(client, db, student, ai_env):
    resp = client.post(
        "/api/v1/ai/chat", json={"message": ""}, headers=auth_headers(student)
    )
    assert resp.status_code == 422
    resp = client.post(
        "/api/v1/ai/chat", json={"message": "x" * 4001}, headers=auth_headers(student)
    )
    assert resp.status_code == 422
