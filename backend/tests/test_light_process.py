"""Light-process collaboration contracts (manual §25-§29, §38, §46-§53).

Actions take effect immediately; the right people get notified; everything
lands in the audit log. Covers WeChat binding, notification fan-out, the
student project-creation switch, and the notification kill switch.
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from app.models.system import AuditLog, Notification
from app.services import runtime_settings
from app.services.runtime_settings import RuntimeSettingsUpdate
from tests.conftest import auth_headers


def set_runtime(db, **overrides) -> None:
    runtime_settings.update_runtime(
        db, RuntimeSettingsUpdate(**overrides), updated_by=None
    )


def notifications_of(db, type: str) -> list[Notification]:
    return list(db.scalars(select(Notification).where(Notification.type == type)))


def notified_user_ids(db, type: str) -> set[int]:
    return {n.user_id for n in notifications_of(db, type)}


def make_lab_project(client, user, name: str, **overrides) -> Any:
    payload = {"name": name, "code": f"{name}-{user.id}", "visibility": "lab"}
    payload.update(overrides)
    return client.post("/api/v1/projects", json=payload, headers=auth_headers(user))


# ---------- notifications replace approvals ----------


def test_task_assign_reassign_due_change_notifications(
    client, db, pi, student, student_b
):
    resp = make_lab_project(client, pi, "NotifyP")
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["data"]["id"]

    # assign -> assignee notified
    resp = client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "notify task",
            "assignee_id": student.id,
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    assert notified_user_ids(db, "task_assigned") == {student.id}

    # reassign -> old AND new assignee notified
    task_id = resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": student_b.id},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert notified_user_ids(db, "task_reassigned") == {student.id, student_b.id}

    # due date change -> current assignee notified
    due = (date.today() + timedelta(days=10)).isoformat()
    resp = client.patch(
        f"/api/v1/tasks/{task_id}", json={"due_date": due}, headers=auth_headers(pi)
    )
    assert resp.status_code == 200
    due_notes = notifications_of(db, "task_due_changed")
    assert {n.user_id for n in due_notes} == {student_b.id}

    # complete -> creator notified, no approval anywhere
    resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "done"},
        headers=auth_headers(student_b),
    )
    assert resp.status_code == 200
    assert notified_user_ids(db, "task_completed") == {pi.id}


def test_project_created_and_member_added_notifications(
    client, db, pi, teacher, student
):
    resp = make_lab_project(client, teacher, "CreatedP")
    assert resp.status_code == 201
    project_id = resp.json()["data"]["id"]
    # the PI (lab director) hears about new projects; the creator does not
    assert notified_user_ids(db, "project_created") == {pi.id}
    assert (
        db.scalar(
            select(AuditLog).where(
                AuditLog.action == "create_project", AuditLog.resource_type == "project"
            )
        )
        is not None
    )

    resp = client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "researcher"},
        headers=auth_headers(teacher),
    )
    assert resp.status_code == 201  # immediate, no acceptance step
    assert notified_user_ids(db, "project_member_added") == {student.id}


def test_student_project_creation_switch(client, db, pi, student):
    # default: students may create projects (lab collaboration first)
    resp = make_lab_project(client, student, "StuP1")
    assert resp.status_code == 201, resp.text

    set_runtime(db, STUDENT_CAN_CREATE_PROJECT=False)
    resp = make_lab_project(client, student, "StuP2")
    assert resp.status_code == 403

    # PI/TEACHER unaffected
    resp = make_lab_project(client, pi, "PiP")
    assert resp.status_code == 201


def test_notification_kill_switch(client, db, pi, student):
    resp = make_lab_project(client, pi, "QuietP")
    assert resp.status_code == 201
    project_id = resp.json()["data"]["id"]

    set_runtime(db, NOTIFICATION_ENABLED=False)
    resp = client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "quiet task",
            "assignee_id": student.id,
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    assert notifications_of(db, "task_assigned") == []
    # the action still succeeded and is audited
    assert (
        db.scalar(select(AuditLog).where(AuditLog.action == "create_task")) is not None
    )


# ---------- WeChat binding ----------


def wechat_login_payload(username: str, password: str, code: str) -> dict:
    return {
        "code": code,
        "username": username,
        "password": password,
        "binding_code": "ABCD1234",
    }


def test_wechat_disabled_by_default(client, db, pi, student):
    resp = client.post("/api/v1/wechat/session", json={"code": "mock:openid-1"})
    assert resp.status_code == 403  # WECHAT_MINIPROGRAM_ENABLED defaults to false


def test_wechat_bind_login_unbind_flow(client, db, pi, student):
    set_runtime(db, WECHAT_MINIPROGRAM_ENABLED=True)

    # PI issues a one-time binding code
    resp = client.post(
        "/api/v1/wechat/binding-codes",
        json={"remark": "for 陈同学"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201, resp.text
    binding_code = resp.json()["data"]["code"]

    # unauthenticated users cannot list codes; neither can students
    assert (
        client.get(
            "/api/v1/wechat/binding-codes", headers=auth_headers(student)
        ).status_code
        == 403
    )

    # session for an unknown openid: not bound yet
    resp = client.post("/api/v1/wechat/session", json={"code": "mock:openid-stu"})
    assert resp.status_code == 200
    assert resp.json()["data"]["bound"] is False

    # wrong password rejected
    resp = client.post(
        "/api/v1/wechat/bind",
        json={
            "code": "mock:openid-stu",
            "username": student.username,
            "password": "wrong-password",
            "binding_code": binding_code,
        },
    )
    assert resp.status_code == 401

    # correct credentials bind and return a usable token
    resp = client.post(
        "/api/v1/wechat/bind",
        json={
            "code": "mock:openid-stu",
            "username": student.username,
            "password": "pass123456",
            "binding_code": binding_code,
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["token"]
    me = client.get(
        "/api/v1/notifications", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert notified_user_ids(db, "wechat_bound") == {pi.id, student.id}
    assert (
        db.scalar(select(AuditLog).where(AuditLog.action == "bind_wechat")) is not None
    )

    # next session with the same openid logs straight in
    resp = client.post("/api/v1/wechat/session", json={"code": "mock:openid-stu"})
    assert resp.status_code == 200
    assert resp.json()["data"]["bound"] is True
    assert resp.json()["data"]["user"]["id"] == student.id

    # the binding code is one-time
    resp = client.post(
        "/api/v1/wechat/bind",
        json={
            "code": "mock:openid-other",
            "username": pi.username,
            "password": "pass123456",
            "binding_code": binding_code,
        },
    )
    assert resp.status_code == 403

    # self-service unbind (after client-side confirm), immediate + audited
    resp = client.delete("/api/v1/wechat/bind", headers=auth_headers(student))
    assert resp.status_code == 200
    resp = client.post("/api/v1/wechat/session", json={"code": "mock:openid-stu"})
    assert resp.json()["data"]["bound"] is False
    assert (
        db.scalar(select(AuditLog).where(AuditLog.action == "unbind_wechat"))
        is not None
    )


def test_wechat_binding_code_expiry(client, db, pi, student):
    from app.core.time import utcnow
    from app.models.wechat import WeChatBindingCode

    set_runtime(db, WECHAT_MINIPROGRAM_ENABLED=True)
    db.add(
        WeChatBindingCode(
            code="EXPIRED01",
            created_by=pi.id,
            expires_at=utcnow() - timedelta(minutes=1),
        )
    )
    db.commit()
    resp = client.post(
        "/api/v1/wechat/bind",
        json={
            "code": "mock:openid-x",
            "username": student.username,
            "password": "pass123456",
            "binding_code": "EXPIRED01",
        },
    )
    assert resp.status_code == 403


# ---------- misc ----------


def test_notification_type_filter_and_read_all(client, db, pi, student):
    make_lab_project(client, pi, "FilterP")
    client.post(
        "/api/v1/tasks",
        json={
            "project_id": client.get(
                "/api/v1/projects", headers=auth_headers(pi)
            ).json()["data"]["items"][0]["id"],
            "title": "filter task",
            "assignee_id": student.id,
        },
        headers=auth_headers(pi),
    )
    resp = client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["unread"] >= 1

    only = client.get(
        "/api/v1/notifications?type=task_assigned", headers=auth_headers(student)
    ).json()["data"]
    assert only["total"] >= 1
    assert all(n["type"] == "task_assigned" for n in only["items"])

    resp = client.post("/api/v1/notifications/read-all", headers=auth_headers(student))
    assert resp.status_code == 200
    unread = client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers(student)
    ).json()["data"]["unread"]
    assert unread == 0
