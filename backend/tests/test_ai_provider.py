"""Provider tests: error mapping, response parsing — no real network."""

import httpx
import pytest

from app.services.ai.errors import (
    AIConfigError,
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIResponseInvalidError,
)
from app.services.ai.provider import FakeLLMProvider, OpenAICompatibleProvider

BASE = "http://fake-llm.local/v1"
KEY = "sk-test"
MODEL = "test-model"


def _provider(handler) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=BASE,
        api_key=KEY,
        model=MODEL,
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )


def _json_response(payload: dict, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return handler


def _ok_payload() -> dict:
    return {
        "model": MODEL,
        "choices": [{"message": {"content": "hello from fake endpoint"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }


@pytest.mark.anyio
async def test_openai_provider_success_and_usage():
    provider = _provider(_json_response(_ok_payload()))
    resp = await provider.chat([{"role": "user", "content": "hi"}])
    assert resp.content == "hello from fake endpoint"
    assert resp.input_tokens == 11
    assert resp.output_tokens == 7
    assert resp.model == MODEL


@pytest.mark.anyio
async def test_openai_provider_auth_error():
    provider = _provider(_json_response({"error": "bad key"}, status=401))
    with pytest.raises(AIProviderAuthError):
        await provider.chat([{"role": "user", "content": "hi"}])


@pytest.mark.anyio
async def test_openai_provider_rate_limit():
    provider = _provider(_json_response({"error": "slow down"}, status=429))
    with pytest.raises(AIProviderRateLimitError):
        await provider.chat([{"role": "user", "content": "hi"}])


@pytest.mark.anyio
async def test_openai_provider_generic_error():
    provider = _provider(_json_response({"error": "boom"}, status=500))
    with pytest.raises(AIProviderError):
        await provider.chat([{"role": "user", "content": "hi"}])


@pytest.mark.anyio
async def test_openai_provider_timeout():
    def slow_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    provider = _provider(slow_handler)
    with pytest.raises(AIProviderTimeoutError):
        await provider.chat([{"role": "user", "content": "hi"}])


@pytest.mark.anyio
async def test_openai_provider_invalid_response():
    provider = _provider(_json_response({"unexpected": True}))
    with pytest.raises(AIResponseInvalidError):
        await provider.chat([{"role": "user", "content": "hi"}])


def test_openai_provider_requires_full_config():
    with pytest.raises(AIConfigError):
        OpenAICompatibleProvider(base_url="", api_key=KEY, model=MODEL)
    with pytest.raises(AIConfigError):
        OpenAICompatibleProvider(base_url=BASE, api_key="", model=MODEL)
    with pytest.raises(AIConfigError):
        OpenAICompatibleProvider(base_url=BASE, api_key=KEY, model="")


@pytest.mark.anyio
async def test_fake_provider_captures_messages():
    fake = FakeLLMProvider(response="captured")
    resp = await fake.chat(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "SECRET-X"}],
        temperature=0.1,
    )
    assert resp.content == "captured"
    assert len(fake.calls) == 1
    assert fake.calls[0].temperature == 0.1
    assert "SECRET-X" in fake.last_messages[-1]["content"]


@pytest.mark.anyio
async def test_fake_provider_raises_configured_error():
    err = AIProviderRateLimitError("simulated 429")
    fake = FakeLLMProvider(error=err)
    with pytest.raises(AIProviderRateLimitError):
        await fake.chat([{"role": "user", "content": "hi"}])
