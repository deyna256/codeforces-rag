"""Tests for EditorialContentParser — covers parse, fetch, extract, clean, segment, LLM, JSON repair."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.parsers.editorial_content_parser import EditorialContentParser
from infrastructure.parsers.errors import (
    EditorialContentFetchError,
    EditorialContentParseError,
    EditorialNotFoundError,
    LLMSegmentationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def http_client():
    return AsyncMock()


@pytest.fixture
def llm_client():
    return AsyncMock()


@pytest.fixture
def parser(http_client, llm_client):
    return EditorialContentParser(http_client=http_client, llm_client=llm_client)


@pytest.fixture
def parser_no_llm(http_client):
    return EditorialContentParser(http_client=http_client, llm_client=None)


# ---------------------------------------------------------------------------
# parse_editorial_content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_editorial_content_empty_urls_raises_not_found(parser):
    with pytest.raises(EditorialNotFoundError):
        await parser.parse_editorial_content("1900", [])


@pytest.mark.asyncio
async def test_parse_editorial_content_success_single_url(parser, http_client, llm_client):
    html = "<html><body><div class='ttypography'>" + "A" * 300 + "</div></body></html>"
    response = MagicMock()
    response.text = html
    http_client.get.return_value = response

    llm_response = json.dumps({
        "problems": [
            {"contest_id": "1900", "problem_id": "A", "start_marker": "AAA", "end_marker": ""}
        ]
    })
    llm_client.complete.return_value = llm_response

    result = await parser.parse_editorial_content("1900", ["http://cf.com/blog/1"])

    assert result.contest_id == "1900"


@pytest.mark.asyncio
async def test_parse_editorial_content_all_urls_fail_raises_fetch_error(parser, http_client):
    http_client.get.side_effect = Exception("network error")

    with pytest.raises(EditorialContentFetchError):
        await parser.parse_editorial_content("1900", ["http://cf.com/blog/1"])


@pytest.mark.asyncio
async def test_parse_editorial_content_partial_failure_continues(parser, http_client, llm_client):
    html = "<html><body><div class='ttypography'>" + "B" * 300 + "</div></body></html>"
    ok_response = MagicMock()
    ok_response.text = html
    http_client.get.side_effect = [Exception("fail"), ok_response]

    llm_response = json.dumps({
        "problems": [
            {"contest_id": "1900", "problem_id": "A", "start_marker": "BBB", "end_marker": ""}
        ]
    })
    llm_client.complete.return_value = llm_response

    result = await parser.parse_editorial_content(
        "1900", ["http://cf.com/blog/bad", "http://cf.com/blog/good"]
    )

    assert result.contest_id == "1900"


# ---------------------------------------------------------------------------
# _fetch_editorial_content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_editorial_content_success(parser, http_client):
    html = "<html><body><div class='ttypography'>" + "X" * 300 + "</div></body></html>"
    response = MagicMock()
    response.text = html
    http_client.get.return_value = response

    text = await parser._fetch_editorial_content("http://cf.com/blog/1")

    assert len(text) > 0


@pytest.mark.asyncio
async def test_fetch_editorial_content_http_error_raises_fetch_error(parser, http_client):
    http_client.get.side_effect = Exception("timeout")

    with pytest.raises(EditorialContentFetchError):
        await parser._fetch_editorial_content("http://cf.com/blog/1")


@pytest.mark.asyncio
async def test_fetch_editorial_content_short_text_raises_parse_error(parser, http_client):
    response = MagicMock()
    response.text = "<html><body><div class='ttypography'>short</div></body></html>"
    http_client.get.return_value = response

    with pytest.raises(EditorialContentParseError):
        await parser._fetch_editorial_content("http://cf.com/blog/1")


# ---------------------------------------------------------------------------
# _extract_blog_content
# ---------------------------------------------------------------------------

def test_extract_blog_content_ttypography_selector(parser):
    from bs4 import BeautifulSoup

    html = "<html><body><div class='ttypography'>" + "Content " * 50 + "</div></body></html>"
    soup = BeautifulSoup(html, "html.parser")

    result = parser._extract_blog_content(soup)

    assert "Content" in result


def test_extract_blog_content_fallback_to_body(parser):
    from bs4 import BeautifulSoup

    html = "<html><body>" + "Fallback " * 10 + "</body></html>"
    soup = BeautifulSoup(html, "html.parser")

    result = parser._extract_blog_content(soup)

    assert "Fallback" in result


def test_extract_blog_content_no_body_returns_empty(parser):
    from bs4 import BeautifulSoup

    html = "<html></html>"
    soup = BeautifulSoup(html, "html.parser")

    result = parser._extract_blog_content(soup)

    assert result == ""


# ---------------------------------------------------------------------------
# _clean_html_content
# ---------------------------------------------------------------------------

def test_clean_html_content_removes_comments_and_scripts(parser):
    from bs4 import BeautifulSoup

    html = (
        "<div>"
        "<script>alert('x')</script>"
        "<div class='comments'>comment</div>"
        "<p>real content</p>"
        "</div>"
    )
    element = BeautifulSoup(html, "html.parser").div

    cleaned = parser._clean_html_content(element)

    text = cleaned.get_text()
    assert "alert" not in text
    assert "comment" not in text
    assert "real content" in text


# ---------------------------------------------------------------------------
# _extract_text_with_structure
# ---------------------------------------------------------------------------

def test_extract_text_with_structure_headings(parser):
    from bs4 import BeautifulSoup

    html = "<div><h2>Section Title</h2><p>paragraph</p></div>"
    element = BeautifulSoup(html, "html.parser").div

    result = parser._extract_text_with_structure(element)

    assert "## Section Title" in result


def test_extract_text_with_structure_code_blocks(parser):
    from bs4 import BeautifulSoup

    html = "<div><pre>int main() {}</pre></div>"
    element = BeautifulSoup(html, "html.parser").div

    result = parser._extract_text_with_structure(element)

    assert "```" in result
    assert "int main()" in result


def test_extract_text_with_structure_paragraphs(parser):
    from bs4 import BeautifulSoup

    html = "<div><p>First paragraph</p><p>Second paragraph</p></div>"
    element = BeautifulSoup(html, "html.parser").div

    result = parser._extract_text_with_structure(element)

    assert "First paragraph" in result
    assert "Second paragraph" in result


# ---------------------------------------------------------------------------
# _clean_extracted_text
# ---------------------------------------------------------------------------

def test_clean_extracted_text_removes_excessive_newlines(parser):
    text = "line1\n\n\n\n\nline2"

    result = parser._clean_extracted_text(text)

    assert "\n\n\n" not in result
    assert "line1" in result
    assert "line2" in result


def test_clean_extracted_text_removes_ui_garbage(parser):
    text = "Real content\nDownload as PDF\nMore real content"

    result = parser._clean_extracted_text(text)

    assert "Download as" not in result
    assert "Real content" in result


# ---------------------------------------------------------------------------
# _combine_editorial_content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_combine_single_item_returns_as_is(parser):
    result = await parser._combine_editorial_content(["only content"])

    assert result == "only content"


@pytest.mark.asyncio
async def test_combine_multiple_items_adds_headers(parser):
    result = await parser._combine_editorial_content(["first", "second"])

    assert "EDITORIAL SOURCE 1" in result
    assert "EDITORIAL SOURCE 2" in result
    assert "first" in result
    assert "second" in result


# ---------------------------------------------------------------------------
# _segment_by_problems
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_segment_no_llm_raises_error(parser_no_llm):
    with pytest.raises(LLMSegmentationError):
        await parser_no_llm._segment_by_problems("x" * 100, "1900", None)


@pytest.mark.asyncio
async def test_segment_short_text_raises_error(parser):
    with pytest.raises(LLMSegmentationError):
        await parser._segment_by_problems("short", "1900", None)


@pytest.mark.asyncio
async def test_segment_success(parser, llm_client):
    editorial_text = "Problem A solution text here. " * 10
    llm_response = json.dumps({
        "problems": [
            {
                "contest_id": "1900",
                "problem_id": "A",
                "start_marker": "Problem A",
                "end_marker": "",
            }
        ]
    })
    llm_client.complete.return_value = llm_response

    result = await parser._segment_by_problems(editorial_text, "1900", None)

    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_segment_llm_error_raises_segmentation_error(parser, llm_client):
    from infrastructure.llm_client import LLMError

    llm_client.complete.side_effect = LLMError("api fail")

    with pytest.raises(LLMSegmentationError):
        await parser._segment_by_problems("x" * 100, "1900", None)


# ---------------------------------------------------------------------------
# _ask_llm_for_segmentation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ask_llm_segmentation_success(parser, llm_client):
    editorial_text = "Problem A\nSolution for A\nProblem B\nSolution for B"
    llm_response = json.dumps({
        "problems": [
            {"contest_id": "1900", "problem_id": "A", "start_marker": "Problem A", "end_marker": "Problem B"},
            {"contest_id": "1900", "problem_id": "B", "start_marker": "Problem B", "end_marker": ""},
        ]
    })
    llm_client.complete.return_value = llm_response

    result = await parser._ask_llm_for_segmentation(editorial_text, "1900", None)

    assert ("1900", "A") in result
    assert ("1900", "B") in result


@pytest.mark.asyncio
async def test_ask_llm_segmentation_truncates_long_text(parser, llm_client):
    long_text = "A" * 400_000
    llm_response = json.dumps({
        "problems": [
            {"contest_id": "1900", "problem_id": "A", "start_marker": "AAA", "end_marker": ""}
        ]
    })
    llm_client.complete.return_value = llm_response

    result = await parser._ask_llm_for_segmentation(long_text, "1900", None)

    # Verify the call was made (truncation happened internally)
    llm_client.complete.assert_called_once()
    call_kwargs = llm_client.complete.call_args
    prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs["prompt"]
    assert "[CONTENT TRUNCATED" in prompt


# ---------------------------------------------------------------------------
# _normalize_problem_id — parametrize
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("input_id", "expected"),
    [
        (None, None),
        ("", None),
        ("A", "A"),
        ("c1", "C1"),
        ("Problem A", "A"),
        ("ЗАДАЧА B", "B"),
        ("1900A", "A"),
        ("1900C1", None),
        ("AB", "AB"),
        ("123", None),
    ],
)
def test_normalize_problem_id(parser, input_id, expected):
    result = parser._normalize_problem_id(input_id)

    assert result == expected


# ---------------------------------------------------------------------------
# _attempt_json_repair
# ---------------------------------------------------------------------------

def test_attempt_json_repair_closes_unclosed_brace(parser):
    broken = '{"problems": [{"a": 1}'

    result = parser._attempt_json_repair(broken)

    assert result is not None
    parsed = json.loads(result)
    assert "problems" in parsed


def test_attempt_json_repair_removes_trailing_comma(parser):
    broken = '{"a": 1, "b": 2,'

    result = parser._attempt_json_repair(broken)

    assert result is not None
    parsed = json.loads(result)
    assert parsed["b"] == 2


def test_attempt_json_repair_closes_unclosed_string(parser):
    broken = '{"a": "unclosed'

    result = parser._attempt_json_repair(broken)

    assert result is not None
    json.loads(result)


def test_attempt_json_repair_unfixable_returns_none(parser):
    broken = "this is not json at all {{{"

    result = parser._attempt_json_repair(broken)

    assert result is None


# ---------------------------------------------------------------------------
# _sanitize_json_string
# ---------------------------------------------------------------------------

def test_sanitize_json_string_escapes_lone_backslash(parser):
    raw = r'{"text": "formula \sqrt{x}"}'

    result = parser._sanitize_json_string(raw)

    parsed = json.loads(result)
    assert "sqrt" in parsed["text"]


def test_sanitize_json_string_preserves_valid_escapes(parser):
    raw = '{"text": "line1\\nline2"}'

    result = parser._sanitize_json_string(raw)

    parsed = json.loads(result)
    assert "line1\nline2" == parsed["text"]


def test_sanitize_json_string_escapes_raw_newline_in_string(parser):
    raw = '{"text": "line1\nline2"}'

    result = parser._sanitize_json_string(raw)

    parsed = json.loads(result)
    assert "line1" in parsed["text"]
    assert "line2" in parsed["text"]


# ---------------------------------------------------------------------------
# _parse_llm_response
# ---------------------------------------------------------------------------

def test_parse_llm_response_markdown_code_block(parser):
    editorial_text = "Problem A solution text here Problem B more text"
    response = '```json\n{"problems": [{"contest_id": "1900", "problem_id": "A", "start_marker": "Problem A", "end_marker": "Problem B"}]}\n```'

    result = parser._parse_llm_response(response, "1900", None, editorial_text)

    assert ("1900", "A") in result


def test_parse_llm_response_no_json_raises_segmentation_error(parser):
    with pytest.raises(LLMSegmentationError):
        parser._parse_llm_response("no json here at all", "1900", None, "text")


def test_parse_llm_response_repair_succeeds(parser):
    editorial_text = "Problem A some text Problem B more text"
    # Truncated JSON — missing closing bracket and brace
    response = '{"problems": [{"contest_id": "1900", "problem_id": "A", "start_marker": "Problem A", "end_marker": "Problem B"}'

    result = parser._parse_llm_response(response, "1900", None, editorial_text)

    assert ("1900", "A") in result


def test_parse_llm_response_repair_fails_raises_segmentation_error(parser):
    response = '{broken json {{{'

    with pytest.raises(LLMSegmentationError):
        parser._parse_llm_response(response, "1900", None, "text")


def test_parse_llm_response_matching_brace_fallback(parser):
    editorial_text = "Problem A solution here and Problem B more"
    response = 'Some prefix text {"problems": [{"contest_id": "1900", "problem_id": "A", "start_marker": "Problem A", "end_marker": "Problem B"}]} trailing'

    result = parser._parse_llm_response(response, "1900", None, editorial_text)

    assert ("1900", "A") in result


# ---------------------------------------------------------------------------
# _find_matching_brace
# ---------------------------------------------------------------------------

def test_find_matching_brace_simple(parser):
    text = '{"a": 1}'

    assert parser._find_matching_brace(text, 0) == 7


def test_find_matching_brace_nested(parser):
    text = '{"a": {"b": 2}}'

    assert parser._find_matching_brace(text, 0) == 14


def test_find_matching_brace_string_with_braces(parser):
    text = '{"a": "}{}"}'

    result = parser._find_matching_brace(text, 0)

    assert result == len(text) - 1


def test_find_matching_brace_no_match_returns_minus_one(parser):
    text = '{"a": 1'

    assert parser._find_matching_brace(text, 0) == -1


# ---------------------------------------------------------------------------
# _extract_text_between_markers
# ---------------------------------------------------------------------------

def test_extract_text_between_markers_start_not_found(parser):
    result = parser._extract_text_between_markers("some text", "NOTFOUND", "end")

    assert result == ""


def test_extract_text_between_markers_end_not_found_takes_rest(parser):
    text = "START marker here and everything after"

    result = parser._extract_text_between_markers(text, "START", "NOTFOUND")

    assert "marker here" in result
    assert "everything after" in result


# ---------------------------------------------------------------------------
# _parse_new_format
# ---------------------------------------------------------------------------

def test_parse_new_format_skips_non_dict_items(parser):
    problems = [
        "not a dict",
        {"contest_id": "1900", "problem_id": "A", "start_marker": "X", "end_marker": ""},
    ]

    result = parser._parse_new_format(problems, "X some editorial text here")

    # The non-dict item is skipped, valid item is processed
    assert isinstance(result, dict)


def test_parse_new_format_no_editorial_text_skips_extraction(parser):
    problems = [
        {"contest_id": "1900", "problem_id": "A", "start_marker": "X", "end_marker": ""},
    ]

    result = parser._parse_new_format(problems, None)

    assert len(result) == 0
