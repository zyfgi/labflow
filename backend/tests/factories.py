"""Shared test factories: only helpers used by three or more test files.

These call the real API so permission rules are exercised end to end.
"""

from tests.conftest import auth_headers


def create_project(
    client, owner, name="测试项目", visibility="lab", code=None, **extra
) -> int:
    resp = client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "code": code or f"T-{owner.id}-{name}",
            "visibility": visibility,
            **extra,
        },
        headers=auth_headers(owner),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def add_project_member(client, owner, project_id, user, role="student") -> None:
    resp = client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": user.id, "project_role": role},
        headers=auth_headers(owner),
    )
    assert resp.status_code == 201, resp.text


def create_task(
    client, owner, project_id, title="测试任务", assignee=None, **extra
) -> int:
    resp = client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": title,
            "assignee_id": assignee.id if assignee else None,
            **extra,
        },
        headers=auth_headers(owner),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def create_experiment(client, owner, project_id, title="测试实验", **extra) -> dict:
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_id, "title": title, **extra},
        headers=auth_headers(owner),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def create_equipment(
    client, admin, asset_no, name="测试设备", category="测试", **extra
) -> int:
    resp = client.post(
        "/api/v1/equipment",
        json={"asset_no": asset_no, "name": name, "category": category, **extra},
        headers=auth_headers(admin),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def create_booking(client, user, equipment_id, start, end, **extra) -> int:
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": start,
            "end_time": end,
            **extra,
        },
        headers=auth_headers(user),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]
