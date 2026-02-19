from unittest.mock import MagicMock

import pytest

from api.exceptions import exception_to_http_response
from infrastructure.errors import CodeforcesEditorialError, ContestNotFoundError
from infrastructure.parsers import ParsingError, URLParsingError


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.url = "http://test/contest"
    return request


def test_url_parsing_error_returns_400(mock_request):
    exc = URLParsingError("bad url")

    response = exception_to_http_response(mock_request, exc)

    assert response.status_code == 400
    assert response.content.error_type == "URLParsingError"
    assert "bad url" in response.content.detail


def test_contest_not_found_error_returns_404(mock_request):
    exc = ContestNotFoundError("Contest 9999 not found")

    response = exception_to_http_response(mock_request, exc)

    assert response.status_code == 404
    assert response.content.error_type == "ContestNotFoundError"


def test_parsing_error_returns_422(mock_request):
    exc = ParsingError("failed to parse")

    response = exception_to_http_response(mock_request, exc)

    assert response.status_code == 422
    assert response.content.error_type == "ParsingError"


def test_codeforces_editorial_error_returns_500(mock_request):
    exc = CodeforcesEditorialError("editorial broken")

    response = exception_to_http_response(mock_request, exc)

    assert response.status_code == 500
    assert response.content.error_type == "CodeforcesEditorialError"


def test_unexpected_exception_returns_500_with_generic_detail(mock_request):
    exc = RuntimeError("something unexpected")

    response = exception_to_http_response(mock_request, exc)

    assert response.status_code == 500
    assert response.content.error_type == "RuntimeError"
    assert response.content.detail == "An unexpected error occurred"
