"""Project & task tests: project-level permissions per PRD §4/§45 Phase E."""

from datetime import date, timedelta

from tests.conftest import auth_headers


def setup_project(client, db, pi, student, student_b, visibility="project_members"):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "轮胎力在线估计", "code": "TIRE-001", "visibility": visibility},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    return project_id


def test_pi_creates_project_and_becomes_owner(client, db, pi):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "车辆参数在线估计", "code": "PARA-001"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["owner_id"] == pi.id
    members = client.get(
        f"/api/v1/projects/{data['id']}/members", headers=auth_headers(pi)
    )
    roles = {m["user_id"]: m["project_role"] for m in members.json()["data"]}
    assert roles[pi.id] == "owner"


def test_duplicate_project_code(client, db, pi):
    client.post(
        "/api/v1/projects",
        json={"name": "A", "code": "DUP-1"},
        headers=auth_headers(pi),
    )
    resp = client.post(
        "/api/v1/projects",
        json={"name": "B", "code": "DUP-1"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 409


def test_private_project_read_tiers(client, db, pi, student, student_b):
    """private = PI/owner/manager only; regular members use project_members."""
    project_id = setup_project(client, db, pi, student, student_b, visibility="private")
    # member of a private project still cannot read it
    resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers(student))
    assert resp.status_code == 403
    # non-member cannot either
    resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers(student_b))
    assert resp.status_code == 403
    # PI can
    assert (
        client.get(
            f"/api/v1/projects/{project_id}", headers=auth_headers(pi)
        ).status_code
        == 200
    )


def test_lab_visible_project_readable_by_any_student(
    client, db, pi, student, student_b
):
    project_id = setup_project(client, db, pi, student, student_b, visibility="lab")
    resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers(student_b))
    assert resp.status_code == 200


def test_student_sees_only_own_projects_in_list(client, db, pi, student, student_b):
    setup_project(client, db, pi, student, student_b, visibility="private")
    resp = client.get("/api/v1/projects", headers=auth_headers(student_b))
    assert resp.json()["data"]["total"] == 0


def test_pi_sees_all_projects(client, db, pi, student, student_b):
    setup_project(client, db, pi, student, student_b, visibility="private")
    resp = client.get("/api/v1/projects", headers=auth_headers(pi))
    assert resp.json()["data"]["total"] == 1


def test_member_cannot_update_project_but_pi_can(client, db, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "P1", "code": "P1-1", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    resp = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"progress": 50},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403
    resp = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"progress": 50},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["progress"] == 50


def test_project_lifecycle(client, db, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "横摆稳定性控制", "code": "YAW-001"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]

    # milestone
    resp = client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json={"title": "完成算法基线", "due_date": date.today().isoformat()},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    milestone_id = resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/milestones/{milestone_id}",
        json={"status": "completed", "progress": 100},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["completed_at"] is not None

    # soft delete
    resp = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers(pi))
    assert resp.status_code == 200
    resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers(pi))
    assert resp.status_code == 404


# ---------- tasks ----------


def _make_project_with_member(client, db, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "TaskProj", "code": f"TASK-{student.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    return project_id


def test_task_lifecycle_and_overdue(client, db, pi, student):
    project_id = _make_project_with_member(client, db, pi, student)
    due = (date.today() - timedelta(days=3)).isoformat()
    resp = client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "CarSim 数据导出",
            "assignee_id": student.id,
            "due_date": due,
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201, resp.text
    task_id = resp.json()["data"]["id"]

    # assignee sees it in my-task list with overdue flag
    resp = client.get("/api/v1/tasks?mine=true", headers=auth_headers(student))
    mine = {t["id"]: t for t in resp.json()["data"]["items"]}
    assert task_id in mine
    assert mine[task_id]["is_overdue"] is True

    # assignee updates status
    resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "in_progress", "progress": 60},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["progress"] == 60

    # done sets 100% + completed_at
    resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "done"},
        headers=auth_headers(student),
    )
    data = resp.json()["data"]
    assert data["progress"] == 100
    assert data["completed_at"] is not None

    # not overdue anymore
    resp = client.get("/api/v1/tasks?mine=true", headers=auth_headers(student))
    mine = {t["id"]: t for t in resp.json()["data"]["items"]}
    assert mine[task_id]["is_overdue"] is False


def test_other_student_cannot_update_task(client, db, pi, student, student_b):
    project_id = _make_project_with_member(client, db, pi, student)
    resp = client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "T1", "assignee_id": student.id},
        headers=auth_headers(pi),
    )
    task_id = resp.json()["data"]["id"]
    resp = client.post(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "done"},
        headers=auth_headers(student_b),
    )
    assert resp.status_code == 403


def test_task_comments(client, db, pi, student):
    project_id = _make_project_with_member(client, db, pi, student)
    resp = client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "T2", "assignee_id": student.id},
        headers=auth_headers(pi),
    )
    task_id = resp.json()["data"]["id"]
    resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "已导出第一版数据"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    resp = client.get(f"/api/v1/tasks/{task_id}/comments", headers=auth_headers(pi))
    comments = resp.json()["data"]
    assert len(comments) == 1
    assert comments[0]["content"] == "已导出第一版数据"


def test_task_assignment_notifies_assignee(client, db, pi, student):
    project_id = _make_project_with_member(client, db, pi, student)
    resp = client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "notify-me",
            "assignee_id": student.id,
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    from sqlalchemy import select

    from app.models.system import Notification

    notes = db.scalars(
        select(Notification).where(Notification.user_id == student.id)
    ).all()
    assert any(n.type == "task_assigned" and n.title == "新任务分配" for n in notes)


def test_search_never_leaks_private_project(client, db, pi, student, student_b):
    """private: regular members lose read access too; search must follow."""
    from tests.factories import add_project_member, create_project

    private_id = create_project(
        client, pi, name="SCOPE 秘密项目", visibility="private", code="SCOPE-SECRET"
    )
    member_project = create_project(
        client, pi, name="成员可见项目", visibility="project_members", code="SCOPE-MEM"
    )
    add_project_member(client, pi, member_project, student)

    for token, user in (
        ("SCOPE-SECRET", student),
        ("SCOPE-SECRET", student_b),
        ("SCOPE-MEM", student_b),
    ):
        resp = client.get(f"/api/v1/search?q={token}", headers=auth_headers(user))
        assert resp.status_code == 200
        assert resp.json()["data"]["projects"] == []

    # member sees the project_members tier; PI sees everything
    resp = client.get("/api/v1/search?q=SCOPE-MEM", headers=auth_headers(student))
    assert any(p["code"] == "SCOPE-MEM" for p in resp.json()["data"]["projects"])
    resp = client.get("/api/v1/search?q=SCOPE", headers=auth_headers(pi))
    assert len(resp.json()["data"]["projects"]) == 2
