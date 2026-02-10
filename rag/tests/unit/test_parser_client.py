import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.parser_client import fetch_contest


class TestFetchContest:
    async def test_success_returns_parsed_response(self):
        response_data = {
            "contest_id": "1920",
            "title": "Round 920",
            "problems": [
                {"contest_id": "1920", "id": "A", "title": "Test Problem"},
            ],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response

        with patch("src.parser_client.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_contest("https://codeforces.com/contest/1920")

        assert result.contest_id == "1920"
        assert result.title == "Round 920"
        assert len(result.problems) == 1
        assert result.problems[0].id == "A"

    async def test_http_error_propagates(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response

        with patch("src.parser_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_contest("https://codeforces.com/contest/9999")
