"""Member / skill / learning plan tests (PRD §29 permission coverage)."""

from tests.conftest import auth_headers, make_user

# ---------- members ----------


def test_pi_can_list_members(client, db, pi, student):
    resp = client.get("/api/v1/members", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 2


def test_student_cannot_list_members(client, student):
    resp = client.get("/api/v1/members", headers=auth_headers(student))
    assert resp.status_code == 403


def test_student_can_view_own_member_detail(client, db, student):
    resp = client.get(f"/api/v1/members/{student.member_profile.id}", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["data"]["user"]["username"] == "student_test"


def test_student_cannot_view_other_member(client, db, student, student_b):
    resp = client.get(
        f"/api/v1/members/{student_b.member_profile.id}", headers=auth_headers(student)
    )
    assert resp.status_code == 403


def test_member_overview_self(client, db, student):
    resp = client.get(
        f"/api/v1/members/{student.member_profile.id}/overview", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["in_progress_tasks"] == 0
    assert data["this_week_report_status"] is None


# ---------- skills ----------


def test_create_skill_by_pi(client, db, pi):
    resp = client.post(
        "/api/v1/skills", json={"name": "ROS2", "category": "工程能力"}, headers=auth_headers(pi)
    )
    assert resp.status_code == 201


def test_student_cannot_create_skill(client, db, student):
    resp = client.post(
        "/api/v1/skills", json={"name": "X"}, headers=auth_headers(student)
    )
    assert resp.status_code == 403


def test_set_and_get_member_skills(client, db, pi, student, student_b):
    skill_resp = client.post(
        "/api/v1/skills", json={"name": "Python"}, headers=auth_headers(pi)
    )
    skill_id = skill_resp.json()["data"]["id"]

    # student edits own skills
    resp = client.put(
        f"/api/v1/members/{student.member_profile.id}/skills",
        json=[{"skill_id": skill_id, "level": 3, "note": "熟悉常用库"}],
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["level"] == 3

    # invalid level rejected
    resp = client.put(
        f"/api/v1/members/{student.member_profile.id}/skills",
        json=[{"skill_id": skill_id, "level": 9}],
        headers=auth_headers(student),
    )
    assert resp.status_code == 422

    # student cannot edit others' skills
    resp = client.put(
        f"/api/v1/members/{student_b_member_id(client, db, pi)}/skills",
        json=[{"skill_id": skill_id, "level": 1}],
        headers=auth_headers(student),
    )
    assert resp.status_code == 403


def student_b_member_id(client, db, pi):
    resp = client.get("/api/v1/members?page_size=100", headers=auth_headers(pi))
    for item in resp.json()["data"]["items"]:
        if item["user"]["username"] == "student_b_test":
            return item["id"]
    raise AssertionError("student_b member not found")


# ---------- learning plans ----------


def test_student_creates_own_plan(client, db, student):
    resp = client.post(
        "/api/v1/learning-plans",
        json={"member_id": student.member_profile.id, "title": "学习线性代数", "progress": 10},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["status"] == "not_started"


def test_student_cannot_create_plan_for_other(client, db, student, student_b):
    resp = client.post(
        "/api/v1/learning-plans",
        json={"member_id": student_b.member_profile.id, "title": "X"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403


def test_student_lists_only_own_plans(client, db, pi, student, student_b):
    client.post(
        "/api/v1/learning-plans",
        json={"member_id": student.member_profile.id, "title": "计划A"},
        headers=auth_headers(student),
    )
    client.post(
        "/api/v1/learning-plans",
        json={"member_id": student_b.member_profile.id, "title": "计划B"},
        headers=auth_headers(student_b),
    )
    resp = client.get("/api/v1/learning-plans", headers=auth_headers(student))
    titles = [item["title"] for item in resp.json()["data"]]
    assert "计划A" in titles
    assert "计划B" not in titles


def test_pi_can_view_and_update_member_plan(client, db, pi, student):
    resp = client.post(
        "/api/v1/learning-plans",
        json={"member_id": student.member_profile.id, "title": "PI可见计划"},
        headers=auth_headers(student),
    )
    plan_id = resp.json()["data"]["id"]

    resp = client.get(
        f"/api/v1/learning-plans?member_id={student.member_profile.id}", headers=auth_headers(pi)
    )
    assert resp.status_code == 200
    assert any(item["title"] == "PI可见计划" for item in resp.json()["data"])

    resp = client.patch(
        f"/api/v1/learning-plans/{plan_id}", json={"progress": 50, "status": "in_progress"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["progress"] == 50


def test_update_plan_invalid_status(client, db, student):
    resp = client.post(
        "/api/v1/learning-plans",
        json={"member_id": student.member_profile.id, "title": "计划X"},
        headers=auth_headers(student),
    )
    plan_id = resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/learning-plans/{plan_id}", json={"status": "bogus"}, headers=auth_headers(student)
    )
    assert resp.status_code == 422
