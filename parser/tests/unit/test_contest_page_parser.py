"""Tests for ContestPageParser — async page parsing, editorial extraction."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.models.parsing import ContestPageData, ProblemData
from infrastructure.parsers.contest_page_parser import ContestPageParser
from infrastructure.parsers.interfaces import ParsingError


@pytest.fixture
def http_client():
    return AsyncMock()


@pytest.fixture
def llm_editorial_finder():
    return AsyncMock()


@pytest.fixture
def parser(http_client, llm_editorial_finder):
    return ContestPageParser(http_client=http_client, llm_editorial_finder=llm_editorial_finder)


CONTEST_HTML = """
<html><body>
<div class="problems">
    <a href="/contest/1900/problem/A">A</a>
</div>
</body></html>
"""

PROBLEM_HTML = """
<html><body>
<div class="problem-statement">
    <div class="header">
        <div class="time-limit">time limit per test: 2 seconds</div>
        <div class="memory-limit">memory limit per test: 256 megabytes</div>
    </div>
    <div class="header"><div class="title">A. Test Problem</div></div>
    <p>Problem description here</p>
</div>
</body></html>
"""


@pytest.mark.asyncio
@patch("infrastructure.parsers.URLParser")
async def test_parse_contest_page_success(mock_url_parser, parser, http_client, llm_editorial_finder):
    mock_url_parser.build_contest_url.return_value = "https://codeforces.com/contest/1900"
    http_client.get_text.return_value = CONTEST_HTML
    llm_editorial_finder.find_editorial_url.return_value = ["https://codeforces.com/blog/entry/123"]

    result = await parser.parse_contest_page("1900")

    assert isinstance(result, ContestPageData)
    assert result.contest_id == "1900"
    assert len(result.editorial_urls) == 1


@pytest.mark.asyncio
@patch("infrastructure.parsers.URLParser")
async def test_parse_contest_page_http_error_raises_parsing_error(
    mock_url_parser, parser, http_client
):
    mock_url_parser.build_contest_url.return_value = "https://codeforces.com/contest/1900"
    http_client.get_text.side_effect = Exception("network error")

    with pytest.raises(ParsingError):
        await parser.parse_contest_page("1900")


@pytest.mark.asyncio
async def test_parse_problem_in_contest_success(parser, http_client):
    http_client.get_text.return_value = PROBLEM_HTML

    result = await parser.parse_problem_in_contest("1900", "A")

    assert isinstance(result, ProblemData)


@pytest.mark.asyncio
async def test_parse_problem_in_contest_error_raises_parsing_error(parser, http_client):
    http_client.get_text.side_effect = Exception("timeout")

    with pytest.raises(ParsingError):
        await parser.parse_problem_in_contest("1900", "A")


@pytest.mark.asyncio
async def test_extract_editorial_url_exception_returns_empty(parser, llm_editorial_finder):
    from bs4 import BeautifulSoup

    llm_editorial_finder.find_editorial_url.side_effect = Exception("llm failed")
    soup = BeautifulSoup("<html></html>", "html.parser")

    result = await parser._extract_editorial_url(soup, "1900")

    assert result == []
