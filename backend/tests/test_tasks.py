import pytest

"""Task business rules: metadata vs status permissions, state timestamps,
cross-resource integrity, deleted-project child isolation."""


from tests.conftest import auth_headers, make_user
from tests.factories import add_project_member, create_project, create_task


@pytest.fixture()
def task_world(client, db, pi, student, student_b):
    project_id = create_project(client, pi, name="任务规则项目", visibility="lab")
    add_project_member(client, pi, project_id, student)
    task_id = create_task(client, pi, project_id, title="规则任务", assignee=student)
    return {"project": project_id, "task": task_id}


def test_assignee_cannot_patch_metadata(client, db, pi, student, task_world):
    for field, value in [
        ("title", "改标题"),
        ("assignee_id", student_b_id(client, pi)),
        ("priority", "critical"),
        ("due_date", "2027-01-01"),
    ]:
        resp = client.patch(
            f"/api/v1/tasks/{task_world['task']}",
            json={field: value},
            headers=auth_headers(student),
        )
        assert resp.status_code == 403, (field, resp.text)


def student_b_id(client, pi):
    resp = client.get("/api/v1/users/options", headers=auth_headers(pi))
    return [
        u["id"] for u in resp.json()["data"] if u["username"].startswith("student_b")
    ][0]


def test_manager_patches_metadata(client, db, pi, task_world):
    resp = client.patch(
        f"/api/v1/tasks/{task_world['task']}",
        json={"title": "管理员改标题", "priority": "high"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["priority"] == "high"


def test_assignee_updates_status_and_progress(client, db, student, task_world):
    resp = client.post(
        f"/api/v1/tasks/{task_world['task']}/status",
        json={"status": "in_progress", "progress": 40},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["progress"] == 40


def test_invalid_status_rejected(client, db, pi, student, task_world):
    resp = client.post(
        f"/api/v1/tasks/{task_world['task']}/status",
        json={"status": "doing"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 422


def test_done_stamps_and_reopen_clears_completed_at(client, db, student, task_world):
    url = f"/api/v1/tasks/{task_world['task']}/status"
    done = client.post(
        url, json={"status": "done"}, headers=auth_headers(student)
    ).json()["data"]
    assert done["progress"] == 100 and done["completed_at"] is not None

    reopened = client.post(
        url, json={"status": "in_progress"}, headers=auth_headers(student)
    ).json()["data"]
    assert reopened["completed_at"] is None

    cancelled = client.post(
        url, json={"status": "cancelled"}, headers=auth_headers(student)
    ).json()["data"]
    assert cancelled["completed_at"] is None


def test_cross_project_milestone_rejected(client, db, pi, student, task_world):
    other_project = create_project(client, pi, name="别的项目")
    resp = client.post(
        f"/api/v1/projects/{other_project}/milestones",
        json={"title": "别人的里程碑"},
        headers=auth_headers(pi),
    )
    milestone_id = resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/tasks/{task_world['task']}",
        json={"milestone_id": milestone_id},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422


def test_cross_project_parent_rejected(client, db, pi, task_world):
    other_project = create_project(client, pi, name="别的项目2")
    other_task = create_task(client, pi, other_project, title="别的任务")
    resp = client.patch(
        f"/api/v1/tasks/{task_world['task']}",
        json={"parent_task_id": other_task},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422


def test_equipment_admin_assignee_rejected(client, db, pi, equip_admin, task_world):
    resp = client.patch(
        f"/api/v1/tasks/{task_world['task']}",
        json={"assignee_id": equip_admin.id},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422


def test_inactive_assignee_rejected(client, db, pi, student, task_world):

    inactive = make_user(db, "inactive_assignee", role="STUDENT")
    client.patch(
        f"/api/v1/users/{inactive.id}",
        json={"status": "inactive"},
        headers=auth_headers(pi),
    )
    resp = client.patch(
        f"/api/v1/tasks/{task_world['task']}",
        json={"assignee_id": inactive.id},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422


def test_non_member_assignee_rejected_on_private(client, db, pi, student_b):
    project_id = create_project(client, pi, name="私有分配", visibility="private")
    task_id = create_task(client, pi, project_id, title="私有任务")
    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": student_b.id},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422


def test_deleted_project_hides_child_tasks(client, db, pi, student, task_world):
    url = f"/api/v1/tasks/{task_world['task']}"

    # assignee loses direct access once the parent project is soft-deleted
    assert (
        client.delete(
            f"/api/v1/projects/{task_world['project']}", headers=auth_headers(pi)
        ).status_code
        == 200
    )
    assert client.get(url, headers=auth_headers(student)).status_code == 404
    assert (
        client.post(
            f"{url}/comments", json={"content": "x"}, headers=auth_headers(student)
        ).status_code
        == 404
    )

    # PI (who can read everything) no longer sees the child task in lists or search
    resp = client.get("/api/v1/tasks", headers=auth_headers(pi))
    assert all(t["id"] != task_world["task"] for t in resp.json()["data"]["items"])
    resp = client.get("/api/v1/search?q=规则任务", headers=auth_headers(pi))
    assert resp.json()["data"]["tasks"] == []
