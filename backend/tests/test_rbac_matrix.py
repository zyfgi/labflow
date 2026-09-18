"""RBAC matrix: role × resource read boundaries via parametrized checks.

Focus is on permission edges, not an endpoint cartesian product.
"""

import pytest

from tests.conftest import auth_headers
from tests.factories import add_project_member, create_project, create_task


@pytest.fixture()
def matrix_world(client, db, pi, teacher, student, student_b):
    """private / project_members / lab projects; student is a member of all."""
    ids = {}
    for visibility in ("private", "project_members", "lab"):
        ids[visibility] = create_project(
            client,
            pi,
            name=f"矩阵-{visibility}",
            visibility=visibility,
            code=f"MX-{visibility}-{pi.id}",
        )
        add_project_member(client, pi, ids[visibility], student)
    create_task(client, pi, ids["lab"], title="矩阵任务")
    return ids


def _get_json(client, url, user):
    resp = client.get(url, headers=auth_headers(user))
    return resp.status_code, resp.json().get("data")


@pytest.mark.parametrize(
    "visibility,expected",
    [
        ("private", 403),
        ("project_members", 200),
        ("lab", 200),
    ],
)
def test_student_member_project_read(
    client, db, matrix_world, student, visibility, expected
):
    code, _ = _get_json(client, f"/api/v1/projects/{matrix_world[visibility]}", student)
    assert code == expected


def test_member_cannot_read_private_project(client, db, matrix_world, student):
    """private denies regular members — that is what project_members is for."""
    code, _ = _get_json(client, f"/api/v1/projects/{matrix_world['private']}", student)
    assert code == 403


def test_non_member_cannot_read_members_project(client, db, matrix_world, student_b):
    code, _ = _get_json(
        client, f"/api/v1/projects/{matrix_world['project_members']}", student_b
    )
    assert code == 403


def test_teacher_reads_lab_but_not_private(client, db, matrix_world, teacher):
    assert (
        _get_json(client, f"/api/v1/projects/{matrix_world['lab']}", teacher)[0] == 200
    )
    assert (
        _get_json(client, f"/api/v1/projects/{matrix_world['private']}", teacher)[0]
        == 403
    )


def test_pi_reads_everything(client, db, matrix_world, pi):
    for pid in matrix_world.values():
        assert _get_json(client, f"/api/v1/projects/{pid}", pi)[0] == 200


# ---------- equipment admin / guest: research denied on every tier ----------


@pytest.fixture()
def equip_admin_member(client, db, pi, matrix_world, equip_admin):
    """Even membership must not leak research data to the equipment admin."""
    add_project_member(client, pi, matrix_world["lab"], equip_admin, role="observer")
    return equip_admin


@pytest.mark.parametrize("visibility", ["private", "project_members", "lab"])
def test_equipment_admin_membership_bypass_blocked(
    client, db, matrix_world, equip_admin_member, visibility
):
    code, _ = _get_json(
        client, f"/api/v1/projects/{matrix_world[visibility]}", equip_admin_member
    )
    assert code == 403


def test_equipment_admin_search_and_retrieval_clean(
    client, db, matrix_world, equip_admin_member
):
    code, data = _get_json(client, "/api/v1/search?q=矩阵", equip_admin_member)
    assert code == 200
    assert data["projects"] == [] and data["tasks"] == []

    resp = client.post(
        "/api/v1/ai/retrieve",
        json={"query": "矩阵项目 矩阵任务"},
        headers=auth_headers(equip_admin_member),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["hits"] == []


# ---------- member-development data boundaries ----------


def test_member_data_visibility(
    client, db, pi, teacher, student, student_b, equip_admin
):
    from datetime import date

    from app.models.learning import LearningPlan
    from app.models.report import WeeklyReport

    s = db
    today = date.today()
    s.add(
        WeeklyReport(
            member_id=student.member_profile.id,
            week_start=today,
            week_end=today,
            status="draft",
        )
    )
    s.add(LearningPlan(member_id=student.member_profile.id, title="学生计划"))
    s.commit()

    student_headers = auth_headers(student)
    staff_headers = auth_headers(pi)
    teacher_headers = auth_headers(teacher)
    admin_headers = auth_headers(equip_admin)
    other_headers = auth_headers(student_b)

    # weekly reports: staff any, student own only, equipment admin none
    assert (
        client.get("/api/v1/weekly-reports", headers=staff_headers).status_code == 200
    )
    assert (
        client.get("/api/v1/weekly-reports", headers=teacher_headers).status_code == 200
    )
    assert (
        client.get("/api/v1/weekly-reports", headers=admin_headers).status_code == 403
    )
    own = client.get("/api/v1/weekly-reports", headers=student_headers).json()["data"]
    assert all(item["member_id"] == student.member_profile.id for item in own["items"])

    # member list: staff only
    assert client.get("/api/v1/members", headers=staff_headers).status_code == 200
    assert client.get("/api/v1/members", headers=other_headers).status_code == 403
    assert client.get("/api/v1/members", headers=admin_headers).status_code == 403

    # learning plans: staff any, student own only
    plans = client.get(
        f"/api/v1/learning-plans?member_id={student.member_profile.id}",
        headers=staff_headers,
    )
    assert plans.status_code == 200
    assert (
        client.get(
            f"/api/v1/learning-plans?member_id={student.member_profile.id}",
            headers=other_headers,
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/learning-plans?member_id={student.member_profile.id}",
            headers=admin_headers,
        ).status_code
        == 403
    )


# ---------- inactive users are locked out everywhere ----------


def test_inactive_user_locked_out(client, db, pi, student):
    client.patch(
        f"/api/v1/users/{student.id}",
        json={"status": "inactive"},
        headers=auth_headers(pi),
    )
    resp = client.get("/api/v1/projects", headers=auth_headers(student))
    assert resp.status_code == 401
