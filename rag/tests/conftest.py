import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-unit-tests")

import pytest  # noqa: E402

from src.models import Chunk, ParserProblem, ParserResponse, Problem  # noqa: E402


@pytest.fixture
def sample_problem():
    return Problem(
        problem_id="1920A",
        contest_id="1920",
        name="Satisfying Constraints",
        rating=1500,
        tags=["math", "implementation"],
        statement="Given n constraints, find a valid integer.",
        editorial="Sort the constraints and check the range.",
        time_limit="2 seconds",
        memory_limit="256 megabytes",
        url="https://codeforces.com/contest/1920/problem/A",
    )


@pytest.fixture
def sample_parser_problem():
    return ParserProblem(
        contest_id="1920",
        id="A",
        title="Satisfying Constraints",
        statement="Given n constraints, find a valid integer.",
        rating=1500,
        tags=["math", "implementation"],
        time_limit="2 seconds",
        memory_limit="256 megabytes",
        explanation="Sort the constraints and check the range.",
    )


@pytest.fixture
def sample_parser_response(sample_parser_problem):
    return ParserResponse(
        contest_id="1920",
        title="Codeforces Round 920",
        problems=[sample_parser_problem],
    )


@pytest.fixture
def sample_chunk():
    return Chunk(
        problem_id="1920A",
        name="Satisfying Constraints",
        rating=1500,
        tags=["math", "implementation"],
        chunk_type="statement",
        text="Given n constraints, find a valid integer.",
    )
