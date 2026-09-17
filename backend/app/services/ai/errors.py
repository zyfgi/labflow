"""AI error taxonomy. Never leak provider details or secrets to the client."""

from app.core.config import settings


class AIError(Exception):
    """Base class; `code` is safe to expose, `detail` never leaves the backend."""

    code = "AI_PROVIDER_ERROR"
    friendly = "AI 服务暂时不可用，请稍后重试。"

    def __init__(self, detail: str = "", friendly: str | None = None):
        super().__init__(detail or self.code)
        self.detail = detail
        if friendly:
            self.friendly = friendly


class AIDisabledError(AIError):
    code = "AI_DISABLED"
    friendly = "AI 助手未启用。"


class AIConfigError(AIError):
    code = "AI_CONFIG_ERROR"
    friendly = "AI 配置有误，请联系管理员。"


class AIProviderTimeoutError(AIError):
    code = "AI_PROVIDER_TIMEOUT"
    friendly = "AI 服务响应超时，请稍后重试。"


class AIProviderAuthError(AIError):
    code = "AI_PROVIDER_AUTH_ERROR"
    friendly = "AI 服务认证失败，请联系管理员。"


class AIProviderRateLimitError(AIError):
    code = "AI_PROVIDER_RATE_LIMIT"
    friendly = "AI 服务请求过于频繁，请稍后重试。"


class AIProviderError(AIError):
    code = "AI_PROVIDER_ERROR"
    friendly = "AI 服务返回错误，请稍后重试。"


class AIResponseInvalidError(AIError):
    code = "AI_RESPONSE_INVALID"
    friendly = "AI 返回内容异常，请重试。"


class AIRateLimitedError(AIError):
    code = "AI_RATE_LIMITED"
    friendly = "请求太频繁，请稍后再试。"


def provider_status() -> dict:
    """Safe status for admin UI: never includes the API key itself."""
    return {
        "ai_enabled": settings.AI_ENABLED,
        "provider": "openai_compatible" if settings.AI_ENABLED else None,
        "model": settings.AI_MODEL or None,
        "api_key": "configured" if settings.AI_API_KEY else "not_configured",
    }
