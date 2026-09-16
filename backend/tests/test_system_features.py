"""Notifications / search / exports / audit-logs / due-checker tests (M8)."""

import io

from app.due_checker import run as run_due_checker
from tests.conftest import auth_headers


# ---------- notifications ----------


def test_notification_flow(client, db, pi, student):
    # trigger a notification: PI assigns a task to student
    resp = client.post(
        "/api/v1/projects",
        json={"name": "NotifyProj", "code": f"NTF-{student.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "notify task", "assignee_id": student.id},
        headers=auth_headers(pi),
    )

    resp = client.get("/api/v1/notifications", headers=auth_headers(student))
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert data["unread"] >= 1
    first = data["items"][0]
    assert first["is_read"] is False

    # mark single read
    resp = client.post(f"/api/v1/notifications/{first['id']}/read", headers=auth_headers(student))
    assert resp.status_code == 200

    # student cannot read others' notification
    resp = client.post(
        f"/api/v1/notifications/{first['id']}/read", headers=auth_headers(pi)
    )
    assert resp.status_code == 404

    # read all
    resp = client.post("/api/v1/notifications/read-all", headers=auth_headers(student))
    assert resp.status_code == 200
    resp = client.get("/api/v1/notifications", headers=auth_headers(student))
    assert resp.json()["data"]["unread"] == 0


# ---------- search ----------


def test_global_search(client, db, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "搜索引擎友好项目", "code": "SEARCH-1", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/experiments",
        json={"project_id": project_id, "title": "SEARCH-EXP-001"},
        headers=auth_headers(pi),
    )

    resp = client.get("/api/v1/search?q=SEARCH", headers=auth_headers(student))
    assert resp.status_code == 200
    results = resp.json()["data"]
    assert any(p["code"] == "SEARCH-1" for p in results["projects"])
    assert any(e["title"] == "SEARCH-EXP-001" for e in results["experiments"])

    # student search has no members section entries
    assert results["members"] == []


def test_search_requires_login(client):
    resp = client.get("/api/v1/search?q=x")
    assert resp.status_code == 401


# ---------- exports ----------


def test_export_members_csv_permission(client, db, pi, student):
    resp = client.get("/api/v1/exports/members", headers=auth_headers(pi))
    assert resp.status_code == 200
    body = resp.content.decode("utf-8-sig")
    assert "姓名" in body
    assert body.count("\n") >= 1

    # student cannot export
    resp = client.get("/api/v1/exports/members", headers=auth_headers(student))
    assert resp.status_code == 403


def test_export_tasks_xlsx(client, db, pi):
    resp = client.get("/api/v1/exports/tasks?format=xlsx", headers=auth_headers(pi))
    assert resp.status_code == 200
    content = resp.content
    # xlsx files are zip containers starting with PK
    assert content[:2] == b"PK"

    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content))
    ws = wb.active
    assert ws.max_row >= 1


def test_export_equipment_requires_admin_role(client, db, pi, equip_admin, student):
    resp = client.get("/api/v1/equipment-bookings", headers=auth_headers(equip_admin))
    assert resp.status_code == 200
    resp = client.get("/api/v1/exports/equipment", headers=auth_headers(student))
    assert resp.status_code == 403
    resp = client.get("/api/v1/exports/equipment", headers=auth_headers(equip_admin))
    assert resp.status_code == 200


# ---------- audit logs ----------


def test_audit_logs_pi_only(client, db, pi, student):
    # generate an audited action
    client.post(
        "/api/v1/projects",
        json={"name": "AuditProj", "code": "AUDIT-1"},
        headers=auth_headers(pi),
    )
    resp = client.get("/api/v1/audit-logs", headers=auth_headers(pi))
    assert resp.status_code == 200
    actions = [item["action"] for item in resp.json()["data"]["items"]]
    assert "create_project" in actions

    resp = client.get("/api/v1/audit-logs", headers=auth_headers(student))
    assert resp.status_code == 403


# ---------- due checker ----------


def test_due_checker_marks_overdue_and_completes_bookings(client, db, pi, equip_admin, student):
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.models.equipment import Equipment, EquipmentBooking, EquipmentBorrow
    from app.models.enums import BookingStatus, BorrowStatus
    from app.models.project import Task
    from app.models.system import Notification

    # overdue task
    resp = client.post(
        "/api/v1/projects",
        json={"name": "DueProj", "code": f"DUE-{student.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    past = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "overdue task", "assignee_id": student.id, "due_date": past},
        headers=auth_headers(pi),
    )

    # borrowed equipment past return time
    eq_resp = client.post(
        "/api/v1/equipment",
        json={"asset_no": f"DUE-EQ-{student.id}", "name": "DueEq", "category": "test"},
        headers=auth_headers(equip_admin),
    )
    eq_id = eq_resp.json()["data"]["id"]
    ret_time = datetime.now() - timedelta(days=1)
    client.post(
        "/api/v1/equipment-borrows",
        json={"equipment_id": eq_id, "expected_return_time": ret_time.strftime("%Y-%m-%dT%H:%M:%S")},
        headers=auth_headers(student),
    )

    stats = run_due_checker()
    assert stats["task_overdue"] >= 1
    assert stats["borrow_overdue"] >= 1

    borrow = db.scalar(select(EquipmentBorrow).where(EquipmentBorrow.equipment_id == eq_id))
    assert borrow.status == BorrowStatus.OVERDUE

    notes = db.scalars(select(Notification).where(Notification.user_id == student.id)).all()
    assert any(n.type == "task_overdue" for n in notes)
    assert any(n.type == "borrow_overdue" for n in notes)

    # idempotent within the same day
    stats2 = run_due_checker()
    assert stats2["task_overdue"] == 0
    assert stats2["borrow_overdue"] == 0
