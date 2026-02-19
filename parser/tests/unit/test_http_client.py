import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.errors import NetworkError, ProblemNotFoundError
from infrastructure.http_client import AsyncHTTPClient


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.http_retries = 1
    return settings


@pytest.fixture
def http_client(mock_settings):
    with patch("infrastructure.http_client.get_settings", return_value=mock_settings):
        client = AsyncHTTPClient(timeout=5)
        client.client = AsyncMock()
        return client


def _mock_response(status_code: int = 200, text: str = "OK"):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


@pytest.mark.asyncio
async def test_get_returns_response_on_success(http_client):
    mock_resp = _mock_response(200)
    http_client.client.get = AsyncMock(return_value=mock_resp)

    result = await http_client.get("https://example.com")

    assert result.status_code == 200


@pytest.mark.asyncio
async def test_get_raises_problem_not_found_on_404(http_client):
    mock_resp = _mock_response(404)
    http_client.client.get = AsyncMock(return_value=mock_resp)

    with pytest.raises(ProblemNotFoundError, match="not found"):
        await http_client.get("https://example.com/missing")


@pytest.mark.asyncio
async def test_get_raises_network_error_on_5xx(http_client):
    mock_resp = _mock_response(500)
    http_client.client.get = AsyncMock(return_value=mock_resp)

    with pytest.raises(NetworkError, match="HTTP error 500"):
        await http_client.get("https://example.com/error")


@pytest.mark.asyncio
async def test_get_raises_network_error_on_connection_failure(http_client):
    http_client.client.get = AsyncMock(side_effect=ConnectionError("refused"))

    with pytest.raises(NetworkError, match="Failed to fetch"):
        await http_client.get("https://example.com/down")


@pytest.mark.asyncio
async def test_get_text_returns_text_body(http_client):
    mock_resp = _mock_response(200, text="page content")
    http_client.client.get = AsyncMock(return_value=mock_resp)

    result = await http_client.get_text("https://example.com")

    assert result == "page content"


@pytest.mark.asyncio
async def test_get_text_decodes_bytes_fallback(http_client):
    mock_resp = MagicMock(spec=[])
    mock_resp.status_code = 200
    mock_resp.content = b"bytes content"
    http_client.client.get = AsyncMock(return_value=mock_resp)

    result = await http_client.get_text("https://example.com")

    assert result == "bytes content"


@pytest.mark.asyncio
async def test_close_suppresses_exceptions(http_client):
    http_client.client.close = AsyncMock(side_effect=RuntimeError("cleanup error"))

    await http_client.close()


@pytest.mark.asyncio
async def test_context_manager_enter_returns_self(http_client):
    result = await http_client.__aenter__()

    assert result is http_client


@pytest.mark.asyncio
async def test_context_manager_exit_calls_close(http_client):
    http_client.client.close = AsyncMock()

    await http_client.__aexit__(None, None, None)

    http_client.client.close.assert_awaited_once()
