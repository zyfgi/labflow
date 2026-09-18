"""Authentication tests per PRD §29: login ok / wrong password / protected API."""

from tests.conftest import auth_headers


def test_login_ok(client, db, pi):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "pi_test", "password": "pass123456"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["username"] == "pi_test"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_login_by_email(client, db, pi):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "pi_test@test.local", "password": "pass123456"},
    )
    assert resp.status_code == 200


def test_login_wrong_password(client, db, pi):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "pi_test", "password": "wrong-pass"}
    )
    assert resp.status_code == 401
    # generic message, must not reveal which part failed
    assert resp.json()["detail"] == "用户名或密码错误"


def test_login_unknown_user_same_message(client, db, pi):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "whatever"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "用户名或密码错误"


def test_me_requires_token(client, db, pi):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_rejects_bad_token(client, db, pi):
    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"}
    )
    assert resp.status_code == 401


def test_me_with_token(client, db, pi):
    headers = auth_headers(pi)
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "pi_test"


def test_change_password_flow(client, db, student):
    headers = auth_headers(student)
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "pass123456", "new_password": "newpass456789"},
        headers=headers,
    )
    assert resp.status_code == 200

    # old password no longer works
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "student_test", "password": "pass123456"},
    )
    assert resp.status_code == 401

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "student_test", "password": "newpass456789"},
    )
    assert resp.status_code == 200


def test_change_password_wrong_old(client, db, student):
    headers = auth_headers(student)
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "incorrect", "new_password": "newpass456789"},
        headers=headers,
    )
    assert resp.status_code == 400
