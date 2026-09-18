"""P0 permission-leak tests (plan §43/§44).

Project B is private; Student A has no access. A unique token string lives in
Project B's description, a task description and an experiment conclusion.

Required behaviour:
- /search?q=<token>          -> 0 results for Student A
- /ai/retrieve q=<token>     -> 0 hits for Student A (PI sees them)
- FakeLLMProvider payload    -> never contains the token (broad question)
- Student B weekly reports   -> never reach Student A's LLM context
"""

import pytest

from app.services.ai.provider import FakeLLMProvider
from tests.conftest import auth_headers, enable_ai

SECRET = "SECRET_PROJECT_B_TOKEN_9F83A"
REPORT_SECRET = "WEEKLY_B_PRIVATE_CONTENT_7C21B"


@pytest.fixture()
def leak_setup(client, db, pi, student, student_b):
    # Project A: lab-visible, student A is a member
    resp = client.post(
        "/api/v1/projects",
        json={"name": "项目A公开", "code": "PA-1", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_a = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_a}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    client.post(
        "/api/v1/experiments",
        json={
            "project_id": project_a,
            "title": "公开实验一",
            "result_summary": "正常结果",
        },
        headers=auth_headers(student),
    )

    # Project B: private, token embedded in project / task / experiment
    resp = client.post(
        "/api/v1/projects",
        json={
            "name": "项目B机密",
            "code": "PB-2",
            "visibility": "private",
            "description": f"机密 {SECRET}",
        },
        headers=auth_headers(pi),
    )
    project_b = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_b}/members",
        json={"user_id": student_b.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    resp = client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_b,
            "title": "机密任务",
            "description": f"task {SECRET}",
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_b, "title": "机密实验"},
        headers=auth_headers(student_b),
    )
    assert resp.status_code == 201
    experiment_id = resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/experiments/{experiment_id}",
        json={"conclusion": f"conclusion {SECRET}"},
        headers=auth_headers(student_b),
    )
    assert resp.status_code == 200

    # Student B weekly report with private content
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": "2026-09-14", "work_summary": f"本周 {REPORT_SECRET}"},
        headers=auth_headers(student_b),
    )
    assert resp.status_code == 201
    return {"project_a": project_a, "project_b": project_b}


def _patch_ai_enabled(db, enabled: bool):
    if enabled:
        enable_ai(db)


def test_search_hides_secret_from_unauthorized(client, db, leak_setup, student):
    resp = client.get(f"/api/v1/search?q={SECRET}", headers=auth_headers(student))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert all(not items for items in data.values()), data


def test_search_finds_secret_for_pi(client, db, leak_setup, pi, student):
    # control: PI can find Project B by code; Student A cannot
    resp = client.get("/api/v1/search?q=PB-2", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert any(p["code"] == "PB-2" for p in resp.json()["data"]["projects"])

    resp = client.get("/api/v1/search?q=PB-2", headers=auth_headers(student))
    assert resp.json()["data"]["projects"] == []


def test_ai_retrieve_hides_secret_from_unauthorized(
    client, db, leak_setup, student, pi
):
    resp = client.post(
        "/api/v1/ai/retrieve",
        json={"query": SECRET},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["hits"] == []

    # control: PI does see Project B data (proves the data exists)
    resp = client.post(
        "/api/v1/ai/retrieve",
        json={"query": SECRET},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["hits"]) > 0


def test_ai_retrieve_no_side_channel_message(client, db, leak_setup, student):
    """Empty hits must be indistinguishable from 'data does not exist'."""
    resp = client.post(
        "/api/v1/ai/retrieve",
        json={"query": SECRET},
        headers=auth_headers(student),
    )
    body = resp.json()
    data = body["data"]
    assert data["hits"] == []
    # no permission wording anywhere (no side channel about existence)
    text = str(body.get("message", "")) + str(data.get("plan", {}).get("intent", ""))
    assert "无权限" not in text and "没有权限" not in text
    # the echoed plan must not contain any hit titles/excerpts (there are none)
    assert all(not items for items in [data["hits"]])


def test_llm_context_never_contains_secret(
    client, db, leak_setup, student, monkeypatch
):
    """Student A asks a broad question; the token must not leak into the
    provider payload even though Project B exists."""
    _patch_ai_enabled(db, True)
    fake = FakeLLMProvider(response="本实验室最近的公开进展总结……")
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: fake)

    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "帮我总结一下最近的项目和实验进展"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    payload = "\n".join(fake.all_messages)
    assert SECRET not in payload
    assert "项目B机密" not in payload
    assert "PB-2" not in payload


def test_weekly_report_never_leaks_to_other_student(
    client, db, leak_setup, student, monkeypatch
):
    """Student A asks about Student B's weekly reports -> nothing in context."""
    _patch_ai_enabled(db, True)
    fake = FakeLLMProvider(response="未找到相关信息")
    monkeypatch.setattr("app.services.ai.service.build_provider", lambda *a, **k: fake)

    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "赵同学最近的周报写了什么"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    payload = "\n".join(fake.all_messages)
    assert REPORT_SECRET not in payload

    # direct retrieval also yields zero report hits from B
    resp = client.post(
        "/api/v1/ai/retrieve",
        json={"query": "赵同学最近周报", "source_types": ["weekly_report"]},
        headers=auth_headers(student),
    )
    hits = resp.json()["data"]["hits"]
    assert hits == []
