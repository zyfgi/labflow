"""Weekly report light-process tests: draft -> publish, no review workflow.

Contract: create draft / publish immediately / published visible to lab
members / author keeps editing after publish / publish & update notify and
audit / peers comment but cannot edit. The review/return/submit endpoints
are gone for good.
"""

from datetime import date, timedelta

from sqlalchemy import select

from app.models.system import AuditLog, Notification
from tests.conftest import auth_headers


def monday(offset_weeks: int = 0) -> date:
    today = date.today()
    base = today - timedelta(days=today.weekday())
    return base + timedelta(weeks=offset_weeks)


def create_report(client, student, week=None, **overrides) -> dict:
    payload = {
        "week_start": (week or monday()).isoformat(),
        "work_summary": "推进了参数估计实验",
        "learning_summary": "学习了 UKF",
        "problems": "收敛速度慢",
        "next_week_plan": "调参",
        "self_progress": 40,
    }
    payload.update(overrides)
    resp = client.post(
        "/api/v1/weekly-reports", json=payload, headers=auth_headers(student)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def publish(client, student, report_id) -> dict:
    resp = client.post(
        f"/api/v1/weekly-reports/{report_id}/publish", headers=auth_headers(student)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_create_draft_and_week_normalized_to_monday(client, student):
    mid_week = monday() + timedelta(days=3)  # Thursday
    report = create_report(client, student, week=mid_week)
    assert report["week_start"] == monday().isoformat()
    assert report["status"] == "draft"


def test_duplicate_same_week_rejected(client, student):
    create_report(client, student)
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": monday().isoformat()},
        headers=auth_headers(student),
    )
    assert resp.status_code == 409


def test_publish_immediate_with_notification_and_audit(
    client, db, pi, teacher, student
):
    report = create_report(client, student)
    data = publish(client, student, report["id"])
    assert data["status"] == "published"
    assert data["published_at"] is not None

    # PI and teacher hear about the publish; the author does not self-notify
    notified = db.scalars(
        select(Notification).where(Notification.type == "weekly_report_published")
    ).all()
    recipients = {n.user_id for n in notified}
    assert recipients == {pi.id, teacher.id}

    assert (
        db.scalar(
            select(AuditLog).where(
                AuditLog.action == "publish_weekly_report",
                AuditLog.resource_id == str(report["id"]),
            )
        )
        is not None
    )


def test_draft_private_published_visible_to_lab(client, pi, student, student_b):
    report = create_report(client, student_b)
    # another student cannot open a draft
    resp = client.get(
        f"/api/v1/weekly-reports/{report['id']}", headers=auth_headers(student)
    )
    assert resp.status_code == 403

    publish(client, student_b, report["id"])
    resp = client.get(
        f"/api/v1/weekly-reports/{report['id']}", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "published"

    # the published report shows up in the peer's default list
    resp = client.get("/api/v1/weekly-reports", headers=auth_headers(student))
    member_ids = {item["member_id"] for item in resp.json()["data"]["items"]}
    assert student_b.member_profile.id in member_ids


def test_author_updates_published_report_no_rereview(client, db, pi, student):
    report = create_report(client, student)
    publish(client, student, report["id"])

    resp = client.patch(
        f"/api/v1/weekly-reports/{report['id']}",
        json={"problems": "UKF 在强噪声下发散，尝试增加过程噪声 Q"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "published"  # stays published, no re-review
    assert data["problems"].startswith("UKF")

    assert (
        db.scalar(
            select(AuditLog).where(
                AuditLog.action == "update_weekly_report",
                AuditLog.resource_id == str(report["id"]),
            )
        )
        is not None
    )
    assert (
        db.scalar(
            select(Notification).where(Notification.type == "weekly_report_updated")
        )
        is not None
    )


def test_peer_comment_on_visible_report(client, db, student, student_b):
    report = create_report(client, student_b)
    publish(client, student_b, report["id"])

    resp = client.post(
        f"/api/v1/weekly-reports/{report['id']}/comments",
        json={"content": "对照实验建议加一组空白样本"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    # the author hears about the comment
    notified = db.scalars(
        select(Notification).where(Notification.type == "weekly_report_commented")
    ).all()
    assert {n.user_id for n in notified} == {student_b.id}

    resp = client.get(
        f"/api/v1/weekly-reports/{report['id']}", headers=auth_headers(student)
    )
    comments = resp.json()["data"]["comments"]
    assert [c["content"] for c in comments] == ["对照实验建议加一组空白样本"]

    # commenting on a draft you cannot see is rejected
    draft = create_report(client, student_b, week=monday(-1))
    resp = client.post(
        f"/api/v1/weekly-reports/{draft['id']}/comments",
        json={"content": "peek"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403


def test_student_cannot_edit_others_report(client, student, student_b):
    report = create_report(client, student_b)
    resp = client.patch(
        f"/api/v1/weekly-reports/{report['id']}",
        json={"work_summary": "not mine"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403


def test_old_review_endpoints_are_gone(client, pi, student):
    report = create_report(client, student)
    for action in ("submit", "review", "return"):
        resp = client.post(
            f"/api/v1/weekly-reports/{report['id']}/{action}", headers=auth_headers(pi)
        )
        assert resp.status_code in (404, 405), f"{action} should not exist"


def test_pi_can_list_all_reports(client, pi, student, student_b):
    create_report(client, student)
    create_report(client, student_b, week=monday(-1))
    resp = client.get("/api/v1/weekly-reports", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 2


def test_report_create_rejects_unknown_fields(client, student):
    """member_id is not part of the create schema and must not be ignored."""
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": monday().isoformat(), "member_id": 999},
        headers=auth_headers(student),
    )
    assert resp.status_code == 422


def test_non_monday_unique_constraint(client, student):
    """Two reports in the same week (different input dates) collapse to one Monday."""
    create_report(client, student, week=monday() + timedelta(days=1))
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": (monday() + timedelta(days=2)).isoformat()},
        headers=auth_headers(student),
    )
    assert resp.status_code == 409


def test_equipment_admin_blocked_from_reports(client, equip_admin, student):
    report = create_report(client, student)
    publish(client, student, report["id"])
    resp = client.get("/api/v1/weekly-reports", headers=auth_headers(equip_admin))
    assert resp.status_code == 403
    resp = client.get(
        f"/api/v1/weekly-reports/{report['id']}", headers=auth_headers(equip_admin)
    )
    assert resp.status_code == 403
