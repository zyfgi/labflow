from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# upload whitelist lives here (not in app.models) to avoid an import cycle
ALLOWED_UPLOAD_EXTENSIONS = [
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

_DEV_DEFAULT_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "LabFlow"
    ENV: str = "development"
    DEBUG: bool = True

    SECRET_KEY: str = _DEV_DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "sqlite:///./labflow.db"
    DB_ECHO: bool = False

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost"

    UPLOAD_DIR: str = "../storage"
    UPLOAD_MAX_MB: int = 100

    # timezone used to resolve "today / this week" in business logic & AI retrieval
    APP_TIMEZONE: str = "Asia/Shanghai"

    # demo seed: when unset, allowed in development and refused in production
    ALLOW_DEMO_SEED: bool | None = None

    # ---- AI assistant (read-only; backend-only credentials) ----
    AI_ENABLED: bool = False
    AI_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_TIMEOUT_SECONDS: int = 60
    AI_MAX_CONTEXT_CHARS: int = 30000
    AI_MAX_RETRIEVAL_HITS: int = 16
    AI_AUDIT_STORE_QUERY: bool = False
    AI_DEBUG_RETRIEVAL: bool | None = None  # None -> enabled in development only
    AI_RATE_LIMIT_PER_MINUTE: int = 10
    AI_RATE_LIMIT_PER_DAY: int = 100

    # accept both DEBUG / LABFLOW_DEBUG etc. (docker-compose uses the prefixed form)
    @model_validator(mode="before")
    @classmethod
    def _accept_prefixed_env(cls, data):
        if isinstance(data, dict):
            for plain, prefixed in (
                ("ENV", "LABFLOW_ENV"),
                ("DEBUG", "LABFLOW_DEBUG"),
                ("SECRET_KEY", "LABFLOW_SECRET_KEY"),
            ):
                if plain not in data and prefixed in data:
                    data[plain] = data[prefixed]
        return data

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def effective_allow_demo_seed(self) -> bool:
        if self.ALLOW_DEMO_SEED is None:
            return not self.is_production
        return self.ALLOW_DEMO_SEED

    @property
    def effective_ai_debug_retrieval(self) -> bool:
        if self.AI_DEBUG_RETRIEVAL is None:
            return not self.is_production
        return self.AI_DEBUG_RETRIEVAL

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def upload_max_bytes(self) -> int:
        return self.UPLOAD_MAX_MB * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def allowed_extensions(self) -> list[str]:
        return ALLOWED_UPLOAD_EXTENSIONS

    def validate_production(self) -> None:
        """Fail fast on unsafe production configuration. Called at app startup."""
        if not self.is_production:
            return
        problems: list[str] = []
        if self.DEBUG:
            problems.append("DEBUG 必须为 false（LABFLOW_DEBUG=false）")
        if not self.SECRET_KEY or self.SECRET_KEY == _DEV_DEFAULT_SECRET:
            problems.append("SECRET_KEY 不能使用开发默认值，请设置随机长密钥")
        elif len(self.SECRET_KEY) < 32:
            problems.append("SECRET_KEY 长度必须 >= 32 字符")
        if self.DATABASE_URL.startswith("sqlite"):
            problems.append("生产环境 DATABASE_URL 不得使用 SQLite，请使用 PostgreSQL")
        if self.AI_ENABLED and not (
            self.AI_BASE_URL and self.AI_API_KEY and self.AI_MODEL
        ):
            problems.append(
                "AI_ENABLED=true 时必须配置 AI_BASE_URL / AI_API_KEY / AI_MODEL"
            )
        if problems:
            raise RuntimeError("生产配置校验失败：\n  - " + "\n  - ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
