"""Tests for services/__init__.py factory functions."""

from unittest.mock import patch, MagicMock

from services import create_problem_service, create_contest_service
from services.problem import ProblemService
from services.contest import ContestService


@patch("infrastructure.parsers.ProblemPageParser")
@patch("infrastructure.codeforces_client.CodeforcesApiClient")
@patch("infrastructure.http_client.AsyncHTTPClient")
def test_create_problem_service_returns_problem_service(
    mock_http_client, mock_api_client, mock_page_parser
):
    result = create_problem_service()

    assert isinstance(result, ProblemService)
    mock_http_client.assert_called_once()
    mock_api_client.assert_called_once()
    mock_page_parser.assert_called_once()


@patch("infrastructure.parsers.EditorialContentParser")
@patch("infrastructure.parsers.ContestPageParser")
@patch("infrastructure.parsers.llm_editorial_finder.LLMEditorialFinder")
@patch("infrastructure.llm_client.OpenRouterClient")
@patch("infrastructure.codeforces_client.CodeforcesApiClient")
@patch("infrastructure.http_client.AsyncHTTPClient")
@patch("config.get_settings")
def test_create_contest_service_returns_contest_service(
    mock_settings,
    mock_http_client,
    mock_api_client,
    mock_llm_client,
    mock_llm_finder,
    mock_page_parser,
    mock_editorial_parser,
):
    settings = MagicMock()
    settings.openrouter_api_key = "sk-or-test"
    settings.openrouter_model = "test-model"
    settings.openrouter_base_url = "http://test"
    mock_settings.return_value = settings

    result = create_contest_service()

    assert isinstance(result, ContestService)
    mock_http_client.assert_called_once()
    mock_api_client.assert_called_once()
    mock_llm_client.assert_called_once()
