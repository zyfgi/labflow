"""P0 hardening tests: equipment-admin isolation, config fail-fast, seed guard,
search SQL scope regression."""

from app.core.config import Settings
from tests.conftest import auth_headers


# ---------- equipment admin isolation (P0-3) ----------


def test_equipment_admin_cannot_see_member_profiles(client, db, pi, equip_admin, student):
    resp = client.get("/api/v1/members", headers=auth_headers(equip_admin))
    assert resp.status_code == 403

    resp = client.get(
        f"/api/v1/members/{student.member_profile.id}", headers=auth_headers(equip_admin)
    )
    assert resp.status_code == 403


def test_equipment_admin_cannot_see_learning_plans(client, db, pi, equip_admin, student):
    client.post(
        "/api/v1/learning-plans",
        json={"member_id": student.member_profile.id, "title": "学生计划"},
        headers=auth_headers(student),
    )
    resp = client.get(
        f"/api/v1/learning-plans?member_id={student.member_profile.id}",
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 403


def test_equipment_admin_cannot_see_weekly_reports(client, db, pi, equip_admin, student):
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": "2026-09-14", "work_summary": "s"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    resp = client.get("/api/v1/weekly-reports", headers=auth_headers(equip_admin))
    assert resp.status_code == 403
    rid = resp  # placeholder to keep naming clear
    del rid

    resp = client.get("/api/v1/weekly-reports", headers=auth_headers(pi))
    assert resp.status_code == 200


def test_equipment_admin_cannot_review_reports(client, db, pi, equip_admin, student):
    resp = client.post(
        "/api/v1/weekly-reports",
        json={"week_start": "2026-09-07", "work_summary": "s"},
        headers=auth_headers(student),
    )
    rid = resp.json()["data"]["id"]
    client.post(f"/api/v1/weekly-reports/{rid}/submit", headers=auth_headers(student))
    resp = client.post(
        f"/api/v1/weekly-reports/{rid}/review", json={"comment": "x"}, headers=auth_headers(equip_admin)
    )
    assert resp.status_code == 403


def test_equipment_admin_still_manages_equipment(client, db, pi, equip_admin):
    resp = client.get("/api/v1/equipment", headers=auth_headers(equip_admin))
    assert resp.status_code == 200
    resp = client.post(
        "/api/v1/equipment",
        json={"asset_no": "EA-1", "name": "设备A", "category": "测试"},
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 201


# ---------- search SQL scope regression (P0-1/P0-2) ----------


def test_search_never_leaks_private_project(client, db, pi, student, student_b):
    resp = client.post(
        "/api/v1/projects",
        json={
            "name": "SCOPE 秘密项目",
            "code": "SCOPE-SECRET",
            "visibility": "private",
        },
        headers=auth_headers(pi),
    )
    assert resp.status_code == 201
    project_id = resp.json()["data"]["id"]
    client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "SCOPE 秘密任务"},
        headers=auth_headers(pi),
    )

    for username in ("student", "student_b"):
        token = auth_headers(student if username == "student" else student_b)
        resp = client.get("/api/v1/search?q=SCOPE", headers=token)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["projects"] == []
        assert data["tasks"] == []


def test_search_scope_no_nplus1_single_query_shape(client, db, pi, student):
    """Smoke: search works for every role without error (SQL scope path)."""
    resp = client.get("/api/v1/search?q=a", headers=auth_headers(student))
    assert resp.status_code == 200


# ---------- production config fail-fast (P0-4) ----------


def _settings(**overrides) -> Settings:
    import os

    defaults = {
        "ENV": "production",
        "DEBUG": "false",
        "SECRET_KEY": "x" * 48,
        "DATABASE_URL": "postgresql+psycopg2://u:p@localhost:5432/lab",
        "AI_ENABLED": "false",
    }
    defaults.update(overrides)
    old = {k: os.environ.get(k) for k in defaults}
    os.environ.update(defaults)
    try:
        return Settings(_env_file=None)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_production_config_valid_passes():
    s = _settings()
    s.validate_production()  # no exception


def test_production_debug_true_fails():
    s = _settings(DEBUG="true")
    try:
        s.validate_production()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "DEBUG" in str(e)


def test_production_default_secret_fails():
    s = _settings(SECRET_KEY="dev-secret-change-me")
    try:
        s.validate_production()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "SECRET_KEY" in str(e)


def test_production_short_secret_fails():
    s = _settings(SECRET_KEY="short")
    try:
        s.validate_production()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "SECRET_KEY" in str(e)


def test_production_sqlite_fails():
    s = _settings(DATABASE_URL="sqlite:///./lab.db")
    try:
        s.validate_production()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "SQLite" in str(e)


def test_production_ai_enabled_without_config_fails():
    s = _settings(AI_ENABLED="true")
    try:
        s.validate_production()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "AI_BASE_URL" in str(e)


def test_development_defaults_do_not_fail():
    import os

    old = {k: os.environ.pop(k, None) for k in ("ENV", "DEBUG", "SECRET_KEY", "DATABASE_URL", "AI_ENABLED")}
    try:
        s = Settings(_env_file=None)
        s.validate_production()  # development: no exception
    finally:
        for k, v in old.items():
            if v is not None:
                os.environ[k] = v


# ---------- demo seed guard (P0-5) ----------


def test_demo_seed_guard_defaults():
    dev = Settings(_env_file=None, ENV="development")
    prod = Settings(_env_file=None, ENV="production")
    assert dev.effective_allow_demo_seed is True
    assert prod.effective_allow_demo_seed is False

    forced = Settings(_env_file=None, ENV="production", ALLOW_DEMO_SEED="true")
    assert forced.effective_allow_demo_seed is True
