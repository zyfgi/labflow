"""RBAC tests: role enforcement is server-side, not just hidden buttons."""

from tests.conftest import auth_headers


def test_pi_can_list_users(client, pi):
    resp = client.get("/api/v1/users", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


def test_student_cannot_list_users(client, student):
    resp = client.get("/api/v1/users", headers=auth_headers(student))
    assert resp.status_code == 403


def test_student_cannot_create_user(client, student):
    resp = client.post(
        "/api/v1/users",
        json={
            "username": "hacker",
            "name": "Hacker",
            "email": "hacker@test.local",
            "role": "PI",
            "password": "pass123456",
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 403


def test_pi_can_create_user(client, db, pi):
    resp = client.post(
        "/api/v1/users",
        json={
            "username": "new_user",
            "name": "新用户",
            "email": "new_user@test.local",
            "role": "STUDENT",
            "password": "pass123456",
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["username"] == "new_user"


def test_duplicate_username_rejected(client, db, pi, student):
    resp = client.post(
        "/api/v1/users",
        json={
            "username": "student_test",
            "name": "dup",
            "email": "dup@test.local",
            "role": "STUDENT",
            "password": "pass123456",
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 409


def test_pi_can_change_role(client, db, pi, student):
    resp = client.patch(
        f"/api/v1/users/{student.id}", json={"role": "TEACHER"}, headers=auth_headers(pi)
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "TEACHER"


def test_student_cannot_change_role(client, db, pi, student, student_b):
    resp = client.patch(
        f"/api/v1/users/{student_b.id}", json={"role": "PI"}, headers=auth_headers(student)
    )
    assert resp.status_code == 403


def test_inactive_user_cannot_authenticate(client, db, pi, student):
    resp = client.patch(
        f"/api/v1/users/{student.id}", json={"status": "inactive"}, headers=auth_headers(pi)
    )
    assert resp.status_code == 200
    resp = client.get("/api/v1/auth/me", headers=auth_headers(student))
    assert resp.status_code == 401


def test_user_options_requires_login(client):
    resp = client.get("/api/v1/users/options")
    assert resp.status_code == 401
