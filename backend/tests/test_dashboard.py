"""Dashboard tests: real aggregates, no hard-coded numbers."""

from tests.conftest import auth_headers


def test_pi_dashboard_shape(client, db, pi, student):
    headers = auth_headers(pi)
    resp = client.get("/api/v1/dashboard/pi", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {
        "kpis",
        "members",
        "projects",
        "attention",
        "activity",
    }
    kpis = data["kpis"]
    assert kpis["member_total"] >= 1
    assert 0 <= kpis["weekly_report_rate"] <= 100
    assert isinstance(data["members"], list)
    assert isinstance(data["projects"], list)
    # attention replaces the old approval inbox: hints, never blockers
    attention = data["attention"]
    assert set(attention.keys()) == {
        "overdue_tasks",
        "overdue_borrows",
        "fault_equipment",
        "stale_projects",
        "due_milestones",
    }


def test_student_cannot_access_pi_dashboard(client, db, student):
    resp = client.get("/api/v1/dashboard/pi", headers=auth_headers(student))
    assert resp.status_code == 403


def test_student_dashboard(client, db, pi, student):
    # assign a task to the student so KPIs are non-trivial
    resp = client.post(
        "/api/v1/projects",
        json={"name": "DashProj", "code": f"DASH-{student.id}", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "dash task",
            "assignee_id": student.id,
        },
        headers=auth_headers(pi),
    )

    resp = client.get("/api/v1/dashboard/student", headers=auth_headers(student))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["kpis"]["tasks_in_progress"] >= 1
    assert any(t["title"] == "dash task" for t in data["tasks"])


def test_dashboard_requires_login(client):
    resp = client.get("/api/v1/dashboard/pi")
    assert resp.status_code == 401
