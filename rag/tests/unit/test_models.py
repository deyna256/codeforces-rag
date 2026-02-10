from src.models import (
    Chunk,
    ParserProblem,
    ParserResponse,
    Problem,
    ProblemListItem,
    SearchRequest,
    SearchResult,
)


class TestParserProblem:
    def test_required_fields_only(self):
        p = ParserProblem(contest_id="1", id="A", title="Test")

        assert p.statement == ""
        assert p.rating is None
        assert p.tags == []
        assert p.time_limit == ""
        assert p.memory_limit == ""
        assert p.explanation is None


class TestParserResponse:
    def test_empty_problems_list(self):
        r = ParserResponse(contest_id="1", title="Round", problems=[])

        assert r.problems == []


class TestProblem:
    def test_required_fields_only(self):
        p = Problem(problem_id="1A", contest_id="1", name="Test")

        assert p.rating is None
        assert p.tags == []
        assert p.statement is None
        assert p.editorial is None
        assert p.url is None


class TestSearchRequest:
    def test_defaults(self):
        r = SearchRequest(query="dp on trees")

        assert r.limit == 10
        assert r.rating_min is None
        assert r.rating_max is None
        assert r.tags is None
        assert r.chunk_type is None

    def test_all_filters(self):
        r = SearchRequest(
            query="dp",
            rating_min=800,
            rating_max=2000,
            tags=["dp", "math"],
            chunk_type="editorial",
            limit=5,
        )

        assert r.rating_min == 800
        assert r.rating_max == 2000
        assert r.tags == ["dp", "math"]
        assert r.chunk_type == "editorial"
        assert r.limit == 5


class TestSearchResult:
    def test_defaults(self):
        r = SearchResult(problem_id="1A", name="Test", score=0.95, snippet="text")

        assert r.rating is None
        assert r.tags == []


class TestProblemListItem:
    def test_defaults(self):
        item = ProblemListItem(problem_id="1A", contest_id="1", name="Test")

        assert item.rating is None
        assert item.tags == []
        assert item.url is None


class TestChunk:
    def test_creation(self):
        c = Chunk(
            problem_id="1A",
            name="Test",
            chunk_type="statement",
            text="some text",
        )

        assert c.rating is None
        assert c.tags == []
        assert c.chunk_type == "statement"
