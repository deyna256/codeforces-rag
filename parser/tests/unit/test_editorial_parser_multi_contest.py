import pytest
from unittest.mock import AsyncMock, MagicMock

from infrastructure.parsers.editorial_content_parser import EditorialContentParser
from infrastructure.parsers.errors import LLMSegmentationError


class TestMultiContestMatching:
    """Test editorial parsing with multiple contests in one blog post."""

    @pytest.fixture
    def parser(self):
        """Create parser with mocked dependencies."""
        http_client = MagicMock()
        llm_client = AsyncMock()
        return EditorialContentParser(http_client, llm_client)

    def test_parse_new_format_with_contest_ids(self, parser):
        editorial_text = """Problem A - Div1
Div1 A solution text here.
Problem A - Div2
Div2 A solution text here.
Problem B - Div1
Div1 B solution text here.
End of editorial"""

        llm_response = """{
            "problems": [
                {"contest_id": "1900", "problem_id": "A", "start_marker": "Problem A - Div1", "end_marker": "Problem A - Div2"},
                {"contest_id": "1901", "problem_id": "A", "start_marker": "Problem A - Div2", "end_marker": "Problem B - Div1"},
                {"contest_id": "1900", "problem_id": "B", "start_marker": "Problem B - Div1", "end_marker": "End of editorial"}
            ]
        }"""

        result = parser._parse_llm_response(llm_response, "1900", None, editorial_text)

        assert len(result) == 3
        assert ("1900", "A") in result
        assert ("1901", "A") in result
        assert ("1900", "B") in result

    def test_parse_old_format_raises_error(self, parser):
        llm_response = """{
            "A": "Problem A solution",
            "B": "Problem B solution"
        }"""

        with pytest.raises(LLMSegmentationError):
            parser._parse_llm_response(llm_response, "1900", None)

    def test_format_expected_problems(self, parser):
        expected = [("1900", "A"), ("1900", "B"), ("1900", "C")]
        formatted = parser._format_expected_problems(expected)

        assert "1900/A" in formatted
        assert "1900/B" in formatted
        assert "1900/C" in formatted

    def test_format_expected_problems_none(self, parser):
        formatted = parser._format_expected_problems(None)
        assert "Unknown" in formatted

    def test_parse_new_format_with_invalid_entries(self, parser):
        editorial_text = """Problem A
Valid entry content here.
Problem B
Missing contest_id content.
Problem C
Empty analysis content.
End"""

        llm_response = """{
            "problems": [
                {"contest_id": "1900", "problem_id": "A", "start_marker": "Problem A", "end_marker": "Problem B"},
                {"contest_id": "", "problem_id": "B", "start_marker": "Problem B", "end_marker": "Problem C"},
                {"contest_id": "1900", "problem_id": "", "start_marker": "Problem C", "end_marker": "End"},
                {"contest_id": "1900", "problem_id": "D", "start_marker": "", "end_marker": ""}
            ]
        }"""

        result = parser._parse_llm_response(llm_response, "1900", None, editorial_text)

        # Only the first entry has valid contest_id, problem_id, and start_marker
        assert len(result) == 1
        assert ("1900", "A") in result

    def test_sanitize_json_with_latex_formulas(self, parser):
        """Test that LaTeX formulas are preserved when using marker-based extraction."""
        editorial_text = r"""
        Problem 2189A - Test Problem

        For $$h \leq l$$, the solution is $$cnt_h \times cnt_l$$

        Problem 2189B - Next Problem
        """

        llm_response = """{
            "problems": [
                {
                    "contest_id": "2189",
                    "problem_id": "A",
                    "start_marker": "Problem 2189A",
                    "end_marker": "Problem 2189B"
                }
            ]
        }"""

        result = parser._parse_llm_response(llm_response, "2189", None, editorial_text)

        assert len(result) == 1
        assert ("2189", "A") in result
        assert r"\leq" in result[("2189", "A")]
        assert r"\times" in result[("2189", "A")]

    def test_parse_llm_response_preserves_valid_escape_sequences(self, parser):
        """Test that valid JSON escape sequences are preserved in markers."""
        editorial_text = """Start of problem A
Line 1
Line 2 Tabbed
End of problems"""

        raw_json = """{
            "problems": [
                {
                    "contest_id": "1900",
                    "problem_id": "A",
                    "start_marker": "Start of problem A",
                    "end_marker": "End of problems"
                }
            ]
        }"""

        result = parser._parse_llm_response(raw_json, "1900", None, editorial_text)

        assert len(result) == 1
        assert ("1900", "A") in result

    def test_real_world_latex_error_from_logs(self, parser):
        """Test the exact error scenario from the production logs with marker-based extraction."""
        editorial_text = r"""Problem 2189A - Math Problem
Note that maximizing the sum is equivalent to maximizing the number of chosen pairs. Without loss of generality, we assume that $$h \leq l$$. For any cell of the table $$(x, y)$$, $$1 \leq x \leq h$$, $$1 \leq y \leq l$$. Let $$cnt_h$$ be the number of elements in the array not exceeding $$h$$, and $$cnt_l$$ be the number of elements not exceeding $$l$$.
Problem 2189B - Next Problem"""

        llm_response = """{
            "problems": [
                {
                    "contest_id": "2189",
                    "problem_id": "A",
                    "start_marker": "Problem 2189A",
                    "end_marker": "Problem 2189B"
                }
            ]
        }"""

        result = parser._parse_llm_response(llm_response, "2189", None, editorial_text)

        assert len(result) == 1
        assert ("2189", "A") in result
        analysis = result[("2189", "A")]
        assert r"\leq" in analysis
        assert "$$h" in analysis
        assert "$$cnt_h$$" in analysis
