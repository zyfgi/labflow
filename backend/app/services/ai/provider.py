"""LLM provider abstraction (Phase 4).

Vendors differ only inside adapters; business code never branches on
provider names. The OpenAI-compatible adapter speaks the standard
`POST {base_url}/chat/completions` protocol over httpx.
"""

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.config import settings
from app.services.ai.errors import (
    AIConfigError,
    AIDisabledError,
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIResponseInvalidError,
)


@dataclass
class ProviderResponse:
    content: str
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> ProviderResponse: ...


class OpenAICompatibleProvider:
    """ Talks to any OpenAI-compatible /chat/completions endpoint. """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        base_url = (base_url or settings.AI_BASE_URL or "").strip()
        api_key = (api_key or settings.AI_API_KEY or "").strip()
        self.model = (model or settings.AI_MODEL or "").strip()
        if not base_url or not api_key or not self.model:
            raise AIConfigError("AI_BASE_URL / AI_API_KEY / AI_MODEL 必须全部配置")
        self._api_key = api_key
        timeout_total = float(timeout_seconds or settings.AI_TIMEOUT_SECONDS)
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=10.0, read=timeout_total, write=30.0, pool=10.0),
            transport=transport,
        )

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        try:
            resp = await self._client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as e:
            raise AIProviderTimeoutError(f"provider timeout: {e.__class__.__name__}")
        except httpx.HTTPError as e:
            raise AIProviderError(f"provider network error: {e.__class__.__name__}")

        if resp.status_code in (401, 403):
            raise AIProviderAuthError(f"provider auth failed: HTTP {resp.status_code}")
        if resp.status_code == 429:
            raise AIProviderRateLimitError("provider rate limited: HTTP 429")
        if resp.status_code >= 400:
            raise AIProviderError(f"provider error: HTTP {resp.status_code}")

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
        except Exception as e:
            raise AIResponseInvalidError(f"provider response unparsable: {e.__class__.__name__}")
        if not content or not str(content).strip():
            raise AIResponseInvalidError("provider returned empty content")
        return ProviderResponse(
            content=str(content),
            model=data.get("model") or self.model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    async def aclose(self) -> None:
        await self._client.aclose()


@dataclass
class _FakeCall:
    messages: list[dict] = field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int | None = None


class FakeLLMProvider:
    """Test double: captures every request; never touches the network.

    Configure `response` (text), or `error` (an AIError subclass instance).
    """

    def __init__(
        self,
        response: str = "FAKE_ANSWER",
        model: str = "fake-model",
        error: Exception | None = None,
        responses: list[str] | None = None,
    ) -> None:
        self.calls: list[_FakeCall] = []
        self._response = response
        self._responses = list(responses or [])
        self._error = error
        self.model = model

    @property
    def last_messages(self) -> list[dict]:
        if not self.calls:
            return []
        return self.calls[-1].messages

    @property
    def all_messages(self) -> list[str]:
        return [m.get("content", "") for call in self.calls for m in call.messages]

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        self.calls.append(_FakeCall(messages=list(messages), temperature=temperature, max_tokens=max_tokens))
        if self._error is not None:
            raise self._error
        text = self._responses.pop(0) if self._responses else self._response
        return ProviderResponse(content=text, model=self.model, input_tokens=10, output_tokens=20)


def build_provider() -> LLMProvider:
    """Factory used by the service layer. Tests inject their own provider."""
    if not settings.AI_ENABLED:
        raise AIDisabledError("AI_ENABLED is false")
    return OpenAICompatibleProvider()
