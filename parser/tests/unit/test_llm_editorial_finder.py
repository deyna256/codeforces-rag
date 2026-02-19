import json

import pytest
from unittest.mock import AsyncMock, patch
from bs4 import BeautifulSoup

from infrastructure.llm_client import LLMError
from infrastructure.parsers.llm_editorial_finder import LLMEditorialFinder


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


CONTEST_PAGE_WITH_LINKS = """
<div>
    <a href="/blog/entry/100">Tutorial for Round 999</a>
    <a href="/blog/entry/101">Editorial Part 2</a>
    <a href="/profile/user123">user123</a>
    <a href="/standings/999">Standings</a>
</div>
"""

CONTEST_PAGE_DUPLICATE_LINKS = """
<div id="sidebar">
    <a href="/blog/entry/100">Tutorial</a>
</div>
<div class="roundbox">
    <a href="/blog/entry/100">Tutorial</a>
    <a href="/blog/entry/101">Another editorial</a>
</div>
"""

CONTEST_PAGE_RELATIVE_LINK = """
<div>
    <a href="/blog/entry/200">Some editorial</a>
</div>
"""


@pytest.fixture
def mock_llm_client():
    return AsyncMock()


@pytest.fixture
def finder(mock_llm_client):
    return LLMEditorialFinder(llm_client=mock_llm_client)


@pytest.fixture
def finder_no_llm():
    return LLMEditorialFinder(llm_client=None)


@pytest.mark.asyncio
async def test_find_editorial_url_without_llm_client_returns_empty(finder_no_llm):
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)

    result = await finder_no_llm.find_editorial_url(soup, "999")

    assert result == []


@pytest.mark.asyncio
async def test_find_editorial_url_with_valid_response_returns_urls(finder, mock_llm_client):
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)
    mock_llm_client.complete.return_value = json.dumps(
        {"urls": ["https://codeforces.com/blog/entry/100"]}
    )

    result = await finder.find_editorial_url(soup, "999")

    assert result == ["https://codeforces.com/blog/entry/100"]


@pytest.mark.asyncio
async def test_find_editorial_url_llm_error_returns_empty(finder, mock_llm_client):
    """LLMError из complete() ловится в _ask_llm_for_editorial и возвращает []."""
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)
    mock_llm_client.complete.side_effect = LLMError("API failed")

    result = await finder.find_editorial_url(soup, "999")

    assert result == []


@pytest.mark.asyncio
async def test_find_editorial_url_invalid_json_returns_empty(finder, mock_llm_client):
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)
    mock_llm_client.complete.return_value = "not valid json {"

    result = await finder.find_editorial_url(soup, "999")

    assert result == []


def test_extract_links_filters_non_editorial_links(finder):
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)

    links = finder._extract_links(soup)

    urls = [link["url"] for link in links]
    assert "https://codeforces.com/blog/entry/100" in urls
    assert "https://codeforces.com/blog/entry/101" in urls
    assert all("/profile/" not in url for url in urls)
    assert all("/standings/" not in url for url in urls)


def test_is_potentially_editorial_link_blog_entry_returns_true(finder):
    assert finder._is_potentially_editorial_link("/blog/entry/12345") is True


@pytest.mark.parametrize(
    "href",
    [
        "/profile/user123",
        "/standings/999",
        "/contest/999",
        "/submission/12345",
        "/register",
        "/settings",
        "javascript:void(0)",
        "#comment",
    ],
)
def test_is_potentially_editorial_link_skip_patterns_returns_false(finder, href):
    assert finder._is_potentially_editorial_link(href) is False


def test_extract_links_deduplicates_urls(finder):
    soup = _make_soup(CONTEST_PAGE_DUPLICATE_LINKS)

    links = finder._extract_links(soup)

    urls = [link["url"] for link in links]
    assert urls.count("https://codeforces.com/blog/entry/100") == 1


def test_extract_links_converts_relative_to_absolute(finder):
    soup = _make_soup(CONTEST_PAGE_RELATIVE_LINK)

    links = finder._extract_links(soup)

    assert len(links) >= 1
    assert links[0]["url"] == "https://codeforces.com/blog/entry/200"


# --- find_editorial_url: непокрытые ветки ---


CONTEST_PAGE_NO_LINKS = """
<div>
    <a href="/profile/user1">User 1</a>
    <a href="/standings/100">Standings</a>
</div>
"""


@pytest.mark.asyncio
async def test_find_editorial_url_no_relevant_links_returns_empty(finder, mock_llm_client):
    """Все ссылки отфильтрованы → _extract_links возвращает [] → строки 42–44."""
    soup = _make_soup(CONTEST_PAGE_NO_LINKS)

    result = await finder.find_editorial_url(soup, "100")

    assert result == []
    mock_llm_client.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_editorial_url_llm_returns_empty_urls(finder, mock_llm_client):
    """LLM вернул {"urls": []} → строки 210–212."""
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)
    mock_llm_client.complete.return_value = json.dumps({"urls": []})

    result = await finder.find_editorial_url(soup, "999")

    assert result == []


# --- _extract_links: непокрытые ветки ---


def test_extract_links_skips_empty_text_links(finder):
    """Ссылка без текста пропускается → строка 94–95."""
    html = """
    <div>
        <a href="/blog/entry/300"></a>
        <a href="/blog/entry/301">   </a>
        <a href="/blog/entry/302">Valid text</a>
    </div>
    """
    soup = _make_soup(html)

    links = finder._extract_links(soup)

    urls = [link["url"] for link in links]
    assert "https://codeforces.com/blog/entry/302" in urls
    assert all("300" not in url and "301" not in url for url in urls)


def test_extract_links_keeps_absolute_urls_unchanged(finder):
    """Абсолютный URL не получает префикс codeforces.com → строка 98 (ветка if не срабатывает)."""
    html = """
    <div>
        <a href="https://example.com/blog/entry/400">External editorial</a>
    </div>
    """
    soup = _make_soup(html)

    links = finder._extract_links(soup)

    assert len(links) == 1
    assert links[0]["url"] == "https://example.com/blog/entry/400"


# --- _ask_llm_for_editorial: непокрытые ветки ---


@pytest.mark.asyncio
async def test_ask_llm_for_editorial_empty_links_returns_empty(finder):
    """Пустой список ссылок → строка 142–143."""
    result = await finder._ask_llm_for_editorial([], "999")

    assert result == []


# --- find_editorial_url: except LLMError / except Exception при ошибке в _extract_links ---


@pytest.mark.asyncio
async def test_find_editorial_url_extract_links_raises_llm_error_returns_empty(
    finder, mock_llm_client
):
    """LLMError поднимается до find_editorial_url → except LLMError → строки 50–52."""
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)
    with patch.object(finder, "_extract_links", side_effect=LLMError("extraction failed")):
        result = await finder.find_editorial_url(soup, "999")

    assert result == []


@pytest.mark.asyncio
async def test_find_editorial_url_extract_links_raises_generic_error_returns_empty(
    finder, mock_llm_client
):
    """Generic exception поднимается до find_editorial_url → except Exception → строки 53–55."""
    soup = _make_soup(CONTEST_PAGE_WITH_LINKS)
    with patch.object(finder, "_extract_links", side_effect=ValueError("broken")):
        result = await finder.find_editorial_url(soup, "999")

    assert result == []


# --- _extract_links: non-string href → строка 82 ---


def test_extract_links_skips_non_string_href(finder):
    """href не является строкой → строка 81–82."""
    html = '<div><a href="/blog/entry/500">Valid</a></div>'
    soup = _make_soup(html)
    # Подменяем href на список (non-string) для первой ссылки
    link_tag = soup.find("a")
    link_tag["href"] = ["/blog/entry/500"]  # list, not str

    links = finder._extract_links(soup)

    assert links == []
