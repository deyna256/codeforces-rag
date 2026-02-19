import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.llm_client import LLMError, OpenRouterClient


@pytest.fixture
def client():
    return OpenRouterClient(api_key="sk-or-test", model="test-model", base_url="https://api.test")


@pytest.fixture
def mock_http():
    """Patch httpx.AsyncClient and yield the mock HTTP client."""
    with patch("infrastructure.llm_client.httpx.AsyncClient") as mock_cls:
        mock = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock


def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    return response


SUCCESS_JSON = {
    "choices": [{"message": {"content": "Hello world"}}],
}


@pytest.mark.asyncio
async def test_complete_success_returns_content(client, mock_http):
    mock_http.post.return_value = _mock_response(json_data=SUCCESS_JSON)

    result = await client.complete("test prompt")

    assert result == "Hello world"


@pytest.mark.asyncio
async def test_complete_with_system_prompt_adds_system_message(client, mock_http):
    mock_http.post.return_value = _mock_response(json_data=SUCCESS_JSON)

    await client.complete("test prompt", system_prompt="be helpful")

    payload = mock_http.post.call_args.kwargs["json"]
    messages = payload["messages"]
    assert messages[0] == {"role": "system", "content": "be helpful"}
    assert messages[1] == {"role": "user", "content": "test prompt"}


@pytest.mark.asyncio
async def test_complete_non_200_raises_llm_error(client, mock_http):
    mock_http.post.return_value = _mock_response(status_code=429, text="rate limited")

    with pytest.raises(LLMError, match="status 429"):
        await client.complete("test prompt")


@pytest.mark.asyncio
async def test_complete_no_choices_raises_llm_error(client, mock_http):
    mock_http.post.return_value = _mock_response(json_data={"choices": []})

    with pytest.raises(LLMError, match="No choices"):
        await client.complete("test prompt")


@pytest.mark.asyncio
async def test_complete_empty_content_raises_llm_error(client, mock_http):
    mock_http.post.return_value = _mock_response(
        json_data={"choices": [{"message": {"content": ""}}]}
    )

    with pytest.raises(LLMError, match="Empty content"):
        await client.complete("test prompt")


@pytest.mark.asyncio
async def test_complete_timeout_raises_llm_error(client, mock_http):
    mock_http.post.side_effect = httpx.TimeoutException("timed out")

    with pytest.raises(LLMError, match="timeout"):
        await client.complete("test prompt")


@pytest.mark.asyncio
async def test_complete_request_error_raises_llm_error(client, mock_http):
    mock_http.post.side_effect = httpx.RequestError("connection failed")

    with pytest.raises(LLMError, match="request error"):
        await client.complete("test prompt")
