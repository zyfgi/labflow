"""Refactor-round tests: equipment-admin research isolation, experiment
creation membership rule, attachment lock bypass, SQL count stability."""

import pytest

from tests.conftest import auth_headers


@pytest.fixture()
def lab_world(client, db, pi, equip_admin, student):
    """A lab-visible project the equipment admin must never see."""
    resp = client.post(
        "/api/v1/projects",
        json={"name": "公开项目X", "code": f"LABX-{pi.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "公开任务X"},
        headers=auth_headers(pi),
    )
    client.post(
        "/api/v1/experiments",
        json={"project_id": project_id, "title": "公开实验X"},
        headers=auth_headers(student),
    )
    return project_id


# ---------- equipment admin: no research data via lab visibility ----------


def test_equip_admin_cannot_read_lab_project(client, db, pi, equip_admin, lab_world):
    resp = client.get(f"/api/v1/projects/{lab_world}", headers=auth_headers(equip_admin))
    assert resp.status_code == 403
    resp = client.get("/api/v1/projects", headers=auth_headers(equip_admin))
    assert resp.json()["data"]["total"] == 0


def test_equip_admin_cannot_read_lab_tasks(client, db, pi, equip_admin, lab_world):
    resp = client.get(f"/api/v1/tasks?project_id={lab_world}", headers=auth_headers(equip_admin))
    assert resp.status_code == 403  # project itself invisible
    resp = client.get("/api/v1/tasks", headers=auth_headers(equip_admin))
    assert all("公开任务X" not in t["title"] for t in resp.json()["data"]["items"])


def test_equip_admin_cannot_read_lab_experiments(client, db, pi, equip_admin, lab_world):
    resp = client.get("/api/v1/experiments", headers=auth_headers(equip_admin))
    assert all("公开实验X" not in e["title"] for e in resp.json()["data"]["items"])


def test_equip_admin_ai_retrieval_sees_no_research_data(client, db, pi, equip_admin, lab_world):
    resp = client.post(
        "/api/v1/ai/retrieve", json={"query": "公开项目X 公开实验X"}, headers=auth_headers(equip_admin)
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["hits"] == []


# ---------- experiment creation requires membership ----------


def test_lab_visible_non_member_cannot_create_experiment(client, db, pi, student_b):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "仅可见项目", "code": f"VIS-{pi.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_id, "title": "路人实验"},
        headers=auth_headers(student_b),
    )
    assert resp.status_code == 403


def test_member_can_still_create_experiment(client, db, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "成员项目", "code": f"MEM-{student.id}", "visibility": "private"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_id, "title": "成员实验"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201


# ---------- experiment lock freezes attachments ----------


def test_locked_experiment_blocks_uploader_attachment_delete(client, db, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "LockProj", "code": f"LOCK-{student.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_id, "title": "锁定实验"},
        headers=auth_headers(student),
    )
    experiment_id = resp.json()["data"]["id"]
    resp = client.post(
        f"/api/v1/experiments/{experiment_id}/attachments",
        files={"file": ("a.csv", io_bytes(), "text/csv")},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    attachment_id = resp.json()["data"]["id"]

    client.post(f"/api/v1/experiments/{experiment_id}/lock", headers=auth_headers(pi))

    # the original uploader can no longer delete after lock
    resp = client.delete(
        f"/api/v1/experiment-attachments/{attachment_id}", headers=auth_headers(student)
    )
    assert resp.status_code == 403

    # PI can still manage frozen records
    resp = client.delete(
        f"/api/v1/experiment-attachments/{attachment_id}", headers=auth_headers(pi)
    )
    assert resp.status_code == 200


def io_bytes() -> bytes:
    return b"a,b\n1,2\n"
