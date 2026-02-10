from src.chunker import MAX_CHUNK_LEN, OVERLAP, _split_text, chunk_problem
from src.models import Problem


class TestSplitText:
    def test_short_text_returns_single_part(self):
        result = _split_text("hello world")

        assert result == ["hello world"]

    def test_exact_max_length_returns_single_part(self):
        text = "a" * MAX_CHUNK_LEN

        result = _split_text(text)

        assert result == [text]

    def test_long_text_splits_with_overlap(self):
        text = "a" * (MAX_CHUNK_LEN + 500)

        result = _split_text(text)

        assert len(result) == 2
        assert len(result[0]) == MAX_CHUNK_LEN
        assert result[0][-OVERLAP:] == result[1][:OVERLAP]

    def test_very_long_text_produces_three_or_more_chunks(self):
        text = "a" * (MAX_CHUNK_LEN * 2 + 500)

        result = _split_text(text)

        assert len(result) >= 3

    def test_empty_text_returns_single_part(self):
        result = _split_text("")

        assert result == [""]

    def test_all_characters_preserved(self):
        text = "abcdef" * 500

        result = _split_text(text)

        reconstructed = result[0]
        for part in result[1:]:
            reconstructed += part[OVERLAP:]
        assert reconstructed == text


class TestChunkProblem:
    def test_statement_only_creates_statement_chunks(self):
        problem = Problem(
            problem_id="1A", contest_id="1", name="P",
            statement="Some statement text", editorial=None,
        )

        chunks = chunk_problem(problem)

        assert len(chunks) == 1
        assert all(c.chunk_type == "statement" for c in chunks)

    def test_editorial_only_creates_editorial_chunks(self):
        problem = Problem(
            problem_id="1A", contest_id="1", name="P",
            statement=None, editorial="Some editorial text",
        )

        chunks = chunk_problem(problem)

        assert len(chunks) == 1
        assert all(c.chunk_type == "editorial" for c in chunks)

    def test_both_fields_creates_statement_and_editorial_chunks(self):
        problem = Problem(
            problem_id="1A", contest_id="1", name="P",
            statement="Statement", editorial="Editorial",
        )

        chunks = chunk_problem(problem)

        types = {c.chunk_type for c in chunks}
        assert types == {"statement", "editorial"}

    def test_no_text_returns_empty_list(self):
        problem = Problem(
            problem_id="1A", contest_id="1", name="P",
            statement=None, editorial=None,
        )

        chunks = chunk_problem(problem)

        assert chunks == []

    def test_preserves_problem_metadata(self, sample_problem):
        chunks = chunk_problem(sample_problem)

        for chunk in chunks:
            assert chunk.problem_id == sample_problem.problem_id
            assert chunk.name == sample_problem.name
            assert chunk.rating == sample_problem.rating
            assert chunk.tags == sample_problem.tags

    def test_long_statement_produces_multiple_chunks(self):
        problem = Problem(
            problem_id="1A", contest_id="1", name="P",
            statement="x" * (MAX_CHUNK_LEN + 500),
        )

        chunks = chunk_problem(problem)

        assert len(chunks) == 2
        assert all(c.chunk_type == "statement" for c in chunks)
