"""Weekly report state machine tests (PRD §29 + §45 Phase D).

draft → submitted → reviewed, plus submitted → returned → edit → resubmit.
"""

from datetime import date, timedelta

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
    resp = client.post("/api/v1/weekly-reports", json=payload, headers=auth_headers(student))
    assert resp.status_code == 201, resp.text
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


def test_full_review_flow(client, db, pi, student):
    report = create_report(client, student)

    # student submits
    resp = client.post(f"/api/v1/weekly-reports/{report['id']}/submit", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "submitted"

    # student can no longer edit a submitted report
    resp = client.patch(
        f"/api/v1/weekly-reports/{report['id']}",
        json={"work_summary": "hacked"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 400

    # student cannot review
    resp = client.post(
        f"/api/v1/weekly-reports/{report['id']}/review",
        json={"comment": "self-approve"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403

    # PI reviews with feedback
    resp = client.post(
        f"/api/v1/weekly-reports/{report['id']}/review",
        json={"comment": "实验设计合理，注意补充对照组"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "reviewed"
    assert data["review_comment"] == "实验设计合理，注意补充对照组"
    assert data["reviewer_id"] == pi.id


def test_return_and_resubmit_flow(client, pi, student):
    report = create_report(client, student)
    client.post(f"/api/v1/weekly-reports/{report['id']}/submit", headers=auth_headers(student))

    resp = client.post(
        f"/api/v1/weekly-reports/{report['id']}/return",
        json={"comment": "问题部分写得太笼统，请具体化"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "returned"

    # student edits the returned report and resubmits
    resp = client.patch(
        f"/api/v1/weekly-reports/{report['id']}",
        json={"problems": "UKF 在强噪声下发散，尝试增加过程噪声 Q"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["problems"].startswith("UKF")

    resp = client.post(f"/api/v1/weekly-reports/{report['id']}/submit", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "submitted"


def test_student_cannot_edit_others_report(client, db, pi, student, student_b):
    report = create_report(client, student_b)
    resp = client.patch(
        f"/api/v1/weekly-reports/{report['id']}",
        json={"work_summary": "not mine"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403

    resp = client.get(f"/api/v1/weekly-reports/{report['id']}", headers=auth_headers(student))
    assert resp.status_code == 403

    # student only sees own reports in list
    create_report(client, student, week=monday(-1))
    resp = client.get("/api/v1/weekly-reports", headers=auth_headers(student))
    member_ids = {item["member_id"] for item in resp.json()["data"]["items"]}
    assert member_ids == {student.member_profile.id}


def test_pi_can_list_all_reports(client, pi, student, student_b):
    create_report(client, student)
    create_report(client, student_b, week=monday(-1))
    resp = client.get("/api/v1/weekly-reports", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 2


def test_student_cannot_create_report_for_other(client, db, student, student_b):
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": monday().isoformat(), "member_id": student_b.member_profile.id},
        headers=auth_headers(student),
    )
    # member_id is not part of the create schema; report goes to own member
    # the created report must belong to the requesting student
    if resp.status_code == 201:
        assert resp.json()["data"]["member_id"] == student.member_profile.id
    else:
        assert resp.status_code in (403, 409)


def test_non_monday_unique_constraint(client, student):
    """Two reports in the same week (different input dates) collapse to one Monday."""
    create_report(client, student, week=monday() + timedelta(days=1))
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": (monday() + timedelta(days=2)).isoformat()},
        headers=auth_headers(student),
    )
    assert resp.status_code == 409
