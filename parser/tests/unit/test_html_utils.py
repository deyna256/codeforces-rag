from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from infrastructure.parsers.html_utils import (
    extract_description,
    extract_memory_limit,
    extract_time_limit,
)


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


PROBLEM_WITH_LIMITS = """
<div class="problem-statement">
    <div class="header">
        <div class="time-limit">time limit per test2 seconds</div>
        <div class="memory-limit">memory limit per test256 megabytes</div>
    </div>
</div>
"""


def test_extract_time_limit_standard_format():
    soup = _make_soup(PROBLEM_WITH_LIMITS)

    result = extract_time_limit(soup)

    assert result == "2 seconds"


def test_extract_time_limit_missing_header_returns_none():
    html = '<div class="problem-statement"><div></div></div>'
    soup = _make_soup(html)

    result = extract_time_limit(soup)

    assert result is None


def test_extract_time_limit_missing_problem_statement_returns_none():
    soup = _make_soup("<div>no problem here</div>")

    result = extract_time_limit(soup)

    assert result is None


def test_extract_memory_limit_standard_format():
    soup = _make_soup(PROBLEM_WITH_LIMITS)

    result = extract_memory_limit(soup)

    assert result == "256 megabytes"


def test_extract_memory_limit_missing_header_returns_none():
    html = '<div class="problem-statement"><div></div></div>'
    soup = _make_soup(html)

    result = extract_memory_limit(soup)

    assert result is None


def test_extract_description_extracts_text_sections():
    html = """
    <div class="problem-statement">
        <div class="header"><div class="title">A. Test</div></div>
        <div class="input-specification">
            <div class="section-title">Input</div>
            <p>Read n integers.</p>
        </div>
        <div class="output-specification">
            <div class="section-title">Output</div>
            <p>Print the answer.</p>
        </div>
    </div>
    """
    soup = _make_soup(html)

    result = extract_description(soup)

    assert result is not None
    assert "Read n integers" in result
    assert "Print the answer" in result


def test_extract_description_missing_statement_returns_none():
    soup = _make_soup("<div>nothing relevant</div>")

    result = extract_description(soup)

    assert result is None


def test_extract_description_fallback_to_full_statement():
    html = """
    <div class="problem-statement">
        <div class="header"><div class="title">A. Fallback</div></div>
        <p>Some problem text without standard sections.</p>
    </div>
    """
    soup = _make_soup(html)

    result = extract_description(soup)

    assert result is not None
    assert "Fallback" in result
    assert "Some problem text" in result


# --- time_limit: ветки без покрытия ---


def test_extract_time_limit_no_time_limit_div_returns_none():
    """Header есть, но div.time-limit отсутствует → строка 28."""
    html = """
    <div class="problem-statement">
        <div class="header">
            <div class="title">A. Test</div>
        </div>
    </div>
    """
    soup = _make_soup(html)

    result = extract_time_limit(soup)

    assert result is None


def test_extract_time_limit_without_label_returns_raw_text():
    """time-limit div без стандартной подписи → строка 24→26 (ветка if не срабатывает)."""
    html = """
    <div class="problem-statement">
        <div class="header">
            <div class="time-limit">5 seconds</div>
        </div>
    </div>
    """
    soup = _make_soup(html)

    result = extract_time_limit(soup)

    assert result == "5 seconds"


# --- memory_limit: ветки без покрытия ---


def test_extract_memory_limit_no_memory_limit_div_returns_none():
    """Header есть, но div.memory-limit отсутствует → строка 53."""
    html = """
    <div class="problem-statement">
        <div class="header">
            <div class="title">A. Test</div>
        </div>
    </div>
    """
    soup = _make_soup(html)

    result = extract_memory_limit(soup)

    assert result is None


def test_extract_memory_limit_missing_problem_statement_returns_none():
    """Нет div.problem-statement → строка 38."""
    soup = _make_soup("<div>no problem here</div>")

    result = extract_memory_limit(soup)

    assert result is None


def test_extract_memory_limit_without_label_returns_raw_text():
    """memory-limit div без стандартной подписи → строка 49→51 (ветка if не срабатывает)."""
    html = """
    <div class="problem-statement">
        <div class="header">
            <div class="memory-limit">512 megabytes</div>
        </div>
    </div>
    """
    soup = _make_soup(html)

    result = extract_memory_limit(soup)

    assert result == "512 megabytes"


# --- extract_description: ветки без покрытия ---


def test_extract_description_only_classless_div():
    """Безымянный div (class=[""]) находится → строки 84–86."""
    html = """
    <div class="problem-statement">
        <div class="header"><div class="title">B. Only Desc</div></div>
        <div class="">This is the main description text.</div>
    </div>
    """
    soup = _make_soup(html)

    result = extract_description(soup)

    assert result is not None
    assert "This is the main description text" in result


def test_extract_description_all_sections_empty_falls_back():
    """Все секции пусты → text_parts пуст → fallback на строке 99."""
    html = """
    <div class="problem-statement">
        <div class="header"><div class="title">C. Empty Sections</div></div>
        <div class="input-specification"></div>
        <div class="output-specification"></div>
        Loose text in statement
    </div>
    """
    soup = _make_soup(html)

    result = extract_description(soup)

    assert result is not None
    assert "Loose text in statement" in result


# --- except Exception ветки ---


def test_extract_time_limit_exception_returns_none():
    """Исключение внутри парсинга → except Exception → строки 29–30."""
    soup = MagicMock()
    soup.find.side_effect = AttributeError("broken soup")

    result = extract_time_limit(soup)

    assert result is None


def test_extract_memory_limit_exception_returns_none():
    """Исключение внутри парсинга → except Exception → строки 54–55."""
    soup = MagicMock()
    soup.find.side_effect = AttributeError("broken soup")

    result = extract_memory_limit(soup)

    assert result is None


def test_extract_description_exception_returns_none():
    """Исключение внутри парсинга → except Exception → строки 101–102."""
    soup = MagicMock()
    soup.find.side_effect = AttributeError("broken soup")

    result = extract_description(soup)

    assert result is None
