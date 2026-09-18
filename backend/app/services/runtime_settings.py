"""Runtime settings: web-editable values stored in system_settings (row id=1),
layered over the static bootstrap config from .env.

- `effective(db)` returns the merged RuntimeSettings; call it once per request.
- The AI API key is write-only: stored encrypted (Fernet key derived from the
  bootstrap SECRET_KEY), never returned by GET.
- APP_TIMEZONE edits require a restart (the tz cache is process-lifetime).
"""

import base64
import hashlib
import json

from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from app.core.config import settings as bootstrap
from app.models.settings import SystemSettings
from app.schemas.base import StrictSchema

_SETTINGS_ID = 1

# secrets are encrypted with a key derived from the bootstrap secret
_FERNET_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(bootstrap.SECRET_KEY.encode()).digest()
)


def _fernet():
    from cryptography.fernet import Fernet

    return Fernet(_FERNET_KEY)


class RuntimeSettings(StrictSchema):
    """Everything a PI can edit from the web UI."""

    APP_NAME: str = "LabFlow"
    APP_TIMEZONE: str = "Asia/Shanghai"
    AI_ENABLED: bool = False
    AI_BASE_URL: str = ""
    AI_MODEL: str = ""
    AI_TIMEOUT_SECONDS: int = Field(default=60, ge=5, le=600)
    AI_MAX_CONTEXT_CHARS: int = Field(default=30000, ge=1000, le=200000)
    AI_MAX_RETRIEVAL_HITS: int = Field(default=16, ge=1, le=50)
    AI_AUDIT_STORE_QUERY: bool = False
    AI_DEBUG_RETRIEVAL: bool = False
    AI_RATE_LIMIT_PER_MINUTE: int = Field(default=10, ge=1, le=1000)
    AI_RATE_LIMIT_PER_DAY: int = Field(default=100, ge=1, le=100000)
    UPLOAD_MAX_MB: int = Field(default=100, ge=1, le=2048)
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = Field(
        default_factory=lambda: [
            "pdf",
            "docx",
            "xlsx",
            "csv",
            "png",
            "jpg",
            "jpeg",
            "zip",
            "txt",
            "md",
        ]
    )

    @field_validator("APP_TIMEZONE")
    @classmethod
    def _check_tz(cls, v: str) -> str:
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError(f"无效的时区: {v}")
        return v

    @field_validator("ALLOWED_UPLOAD_EXTENSIONS")
    @classmethod
    def _check_extensions(cls, v: list[str]) -> list[str]:
        cleaned = [e.strip().lstrip(".").lower() for e in v if e.strip()]
        if not cleaned:
            raise ValueError("上传扩展名不能为空")
        return cleaned


class RuntimeSettingsUpdate(RuntimeSettings):
    """PATCH payload; every field optional. AI_API_KEY write-only:

    absent -> keep old, empty string -> keep old, clear_ai_api_key -> remove.
    """

    AI_API_KEY: str | None = Field(default=None, max_length=500)
    clear_ai_api_key: bool = False


def get_row(db: Session) -> SystemSettings:
    row = db.get(SystemSettings, _SETTINGS_ID)
    if row is None:
        row = SystemSettings(id=_SETTINGS_ID, config_json={})
        db.add(row)
        db.flush()
    return row


def effective(db: Session) -> RuntimeSettings:
    """Merged view: bootstrap defaults overridden by the stored JSON document."""
    row = get_row(db)
    data = dict(row.config_json or {})
    data.setdefault("APP_NAME", bootstrap.APP_NAME)
    data.setdefault("APP_TIMEZONE", bootstrap.APP_TIMEZONE)
    data = {k: v for k, v in data.items() if k in RuntimeSettings.model_fields}
    if "AI_DEBUG_RETRIEVAL" not in data:
        # debug retrieval follows the environment unless explicitly pinned
        data["AI_DEBUG_RETRIEVAL"] = not bootstrap.is_production
    return RuntimeSettings.model_validate(data)


def _decrypt_secret(row: SystemSettings) -> str:
    if not row.encrypted_secrets:
        return ""
    try:
        return _fernet().decrypt(row.encrypted_secrets.encode()).decode()
    except Exception:
        return ""


def get_ai_api_key(db: Session) -> str:
    """Decrypted runtime key; falls back to the bootstrap env value."""
    row = get_row(db)
    stored = _decrypt_secret(row)
    return stored or bootstrap.AI_API_KEY


def update_runtime(
    db: Session, payload: RuntimeSettingsUpdate, updated_by: int
) -> RuntimeSettings:
    row = get_row(db)
    data = row.config_json or {}
    for field, value in payload.model_dump(
        exclude_unset=True, exclude={"AI_API_KEY", "clear_ai_api_key"}
    ).items():
        data[field] = value
    row.config_json = data

    if payload.clear_ai_api_key:
        row.encrypted_secrets = None
    elif payload.AI_API_KEY:
        row.encrypted_secrets = _fernet().encrypt(payload.AI_API_KEY.encode()).decode()
    row.updated_by = updated_by
    from app.core.time import utcnow

    row.updated_at = utcnow()
    db.commit()
    return effective(db)


def read_stored_config_json(db: Session) -> dict:
    return dict(get_row(db).config_json or {})


def bootstrap_summary() -> dict:
    """Read-only deployment values, secrets masked."""
    db_url = bootstrap.DATABASE_URL
    if "@" in db_url:
        scheme, rest = db_url.split("://", 1)
        creds, _, host = rest.rpartition("@")
        user = creds.split(":", 1)[0]
        db_url = f"{scheme}://{user}:***@{host}"
    return {
        "ENV": bootstrap.ENV,
        "DEBUG": bootstrap.DEBUG,
        "DATABASE_URL": db_url,
        "SECRET_KEY": "configured",
        "CORS_ORIGINS": bootstrap.CORS_ORIGINS,
        "UPLOAD_DIR": bootstrap.UPLOAD_DIR,
        "DB_ECHO": bootstrap.DB_ECHO,
    }


def to_admin_view(db: Session) -> dict:
    """GET payload: runtime values + masked bootstrap section."""
    runtime = effective(db)
    row = get_row(db)
    return {
        "runtime": runtime.model_dump(exclude={"AI_API_KEY"}),
        "AI_API_KEY_CONFIGURED": bool(_decrypt_secret(row) or bootstrap.AI_API_KEY),
        "bootstrap": bootstrap_summary(),
        "restart_required": ["APP_TIMEZONE"],
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def export_stored_json(db: Session) -> str:
    return json.dumps(read_stored_config_json(db), ensure_ascii=False)
