"""System settings: PI-only access, secret handling, audit, persistence."""

import pytest
from sqlalchemy import select

from app.models.system import AuditLog
from app.services import runtime_settings
from tests.conftest import auth_headers


@pytest.fixture()
def settings_row(db):
    """Make sure the singleton row exists."""
    runtime_settings.get_row(db)
    return db


def test_get_settings_pi_only(client, db, pi, student, equip_admin):
    resp = client.get("/api/v1/system/settings", headers=auth_headers(pi))
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert "runtime" in body and "bootstrap" in body

    resp = client.get("/api/v1/system/settings", headers=auth_headers(student))
    assert resp.status_code == 403
    resp = client.get("/api/v1/system/settings", headers=auth_headers(equip_admin))
    assert resp.status_code == 403


def test_patch_runtime_setting_persists(client, db, pi):
    resp = client.patch(
        "/api/v1/system/settings",
        json={"AI_MODEL": "glm-5", "AI_TIMEOUT_SECONDS": 30},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["runtime"]["AI_MODEL"] == "glm-5"
    assert resp.json()["data"]["runtime"]["AI_TIMEOUT_SECONDS"] == 30

    # persisted: a fresh read returns the same values
    resp = client.get("/api/v1/system/settings", headers=auth_headers(pi))
    assert resp.json()["data"]["runtime"]["AI_MODEL"] == "glm-5"


def test_invalid_values_rejected(client, db, pi):
    resp = client.patch(
        "/api/v1/system/settings",
        json={"AI_TIMEOUT_SECONDS": 1},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422

    resp = client.patch(
        "/api/v1/system/settings",
        json={"APP_TIMEZONE": "Mars/Olympus"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422


def test_ai_key_write_only_and_encrypted(client, db, pi, student):
    resp = client.patch(
        "/api/v1/system/settings",
        json={"AI_ENABLED": True, "AI_API_KEY": "sk-super-secret-123"},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["AI_API_KEY_CONFIGURED"] is True
    # the raw key never appears anywhere in the response
    assert "sk-super-secret-123" not in resp.text

    # encrypted at rest
    row = runtime_settings.get_row(db)
    assert row.encrypted_secrets
    assert "sk-super-secret-123" not in row.encrypted_secrets
    assert runtime_settings.get_ai_api_key(db) == "sk-super-secret-123"

    # patch without key keeps the old value
    resp = client.patch(
        "/api/v1/system/settings", json={"AI_MODEL": "m2"}, headers=auth_headers(pi)
    )
    assert runtime_settings.get_ai_api_key(db) == "sk-super-secret-123"

    # clearing removes it
    resp = client.patch(
        "/api/v1/system/settings",
        json={"clear_ai_api_key": True},
        headers=auth_headers(pi),
    )
    assert resp.json()["data"]["AI_API_KEY_CONFIGURED"] is False
    assert runtime_settings.get_ai_api_key(db) == ""


def test_bootstrap_values_masked(client, db, pi):
    resp = client.get("/api/v1/system/settings", headers=auth_headers(pi))
    bootstrap = resp.json()["data"]["bootstrap"]
    assert bootstrap["SECRET_KEY"] == "configured"
    assert bootstrap["ENV"]
    if "@" in bootstrap["DATABASE_URL"]:
        assert "***" in bootstrap["DATABASE_URL"]


def test_settings_update_writes_audit_log(client, db, pi):
    client.patch(
        "/api/v1/system/settings",
        json={"AI_MODEL": "audited-model"},
        headers=auth_headers(pi),
    )
    logs = db.scalars(
        select(AuditLog).where(AuditLog.action == "update_settings")
    ).all()
    assert logs
    detail = str(logs[-1].detail_json)
    assert "AI_MODEL" in detail
    # no secrets in audit trail
    assert "AI_API_KEY" not in detail


def test_unknown_setting_field_rejected(client, db, pi):
    resp = client.patch(
        "/api/v1/system/settings",
        json={"DEFINITELY_NOT_A_SETTING": 1},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 422


def test_ai_connection_requires_config(client, db, pi):
    resp = client.post("/api/v1/system/settings/ai/test", headers=auth_headers(pi))
    assert resp.status_code == 400  # disabled / incomplete config


# ---------- production config fail-fast ----------


def _settings(**overrides):
    import os

    from app.core.config import Settings

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
    _settings().validate_production()


@pytest.mark.parametrize(
    "bad,needle",
    [
        ({"DEBUG": "true"}, "DEBUG"),
        ({"SECRET_KEY": "dev-secret-change-me"}, "SECRET_KEY"),
        ({"SECRET_KEY": "short"}, "SECRET_KEY"),
        ({"DATABASE_URL": "sqlite:///./lab.db"}, "SQLite"),
        ({"AI_ENABLED": "true"}, "AI_BASE_URL"),
    ],
)
def test_production_config_failures(bad, needle):
    with pytest.raises(RuntimeError) as exc:
        _settings(**bad).validate_production()
    assert needle in str(exc.value)


def test_demo_seed_guard_defaults():
    from app.core.config import Settings

    dev = Settings(_env_file=None, ENV="development")
    prod = Settings(_env_file=None, ENV="production")
    assert dev.effective_allow_demo_seed is True
    assert prod.effective_allow_demo_seed is False
    forced = Settings(_env_file=None, ENV="production", ALLOW_DEMO_SEED="true")
    assert forced.effective_allow_demo_seed is True
