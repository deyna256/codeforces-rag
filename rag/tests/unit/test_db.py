from unittest.mock import MagicMock

from src.db import (
    COLLECTION,
    get_loaded_contest_ids,
    get_problem_text,
    get_problems,
    qdrant_search,
    qdrant_upsert_chunks,
    upsert_problem,
)
from src.models import Chunk


class TestUpsertProblem:
    async def test_executes_insert_query(self, mock_pg_conn, sample_problem):
        await upsert_problem(sample_problem)

        mock_pg_conn.execute.assert_awaited_once()
        args = mock_pg_conn.execute.call_args[0]
        assert "INSERT INTO problems" in args[0]
        assert args[1] == sample_problem.problem_id
        assert args[2] == sample_problem.contest_id
        assert args[3] == sample_problem.name


class TestGetLoadedContestIds:
    async def test_returns_contest_ids(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = [
            {"contest_id": "1920"},
            {"contest_id": "1921"},
        ]

        result = await get_loaded_contest_ids()

        assert result == ["1920", "1921"]
        query = mock_pg_conn.fetch.call_args[0][0]
        assert "DISTINCT contest_id" in query
        assert "ORDER BY contest_id" in query

    async def test_returns_empty_list_when_no_contests(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = []

        result = await get_loaded_contest_ids()

        assert result == []


class TestGetProblems:
    async def test_no_filters_returns_all(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = [
            {
                "problem_id": "1A",
                "contest_id": "1",
                "name": "Test",
                "rating": 1500,
                "tags": ["dp"],
                "url": None,
            }
        ]

        result = await get_problems()

        assert len(result) == 1
        assert result[0].problem_id == "1A"
        assert result[0].rating == 1500
        assert result[0].tags == ["dp"]

    async def test_rating_filter_builds_correct_query(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = []

        await get_problems(rating_min=1000, rating_max=2000)

        query = mock_pg_conn.fetch.call_args[0][0]
        assert "rating >= $1" in query
        assert "rating <= $2" in query

    async def test_tags_filter_builds_correct_query(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = []

        await get_problems(tags=["dp", "math"])

        query = mock_pg_conn.fetch.call_args[0][0]
        assert "tags && $1" in query

    async def test_contest_id_filter_builds_correct_query(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = []

        await get_problems(contest_id="1920")

        query = mock_pg_conn.fetch.call_args[0][0]
        assert "contest_id = $1" in query

    async def test_combined_filters_use_sequential_params(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = []

        await get_problems(rating_min=1000, rating_max=2000, tags=["dp"])

        args = mock_pg_conn.fetch.call_args[0]
        query = args[0]
        assert "rating >= $1" in query
        assert "rating <= $2" in query
        assert "tags && $3" in query
        assert "LIMIT $4" in query
        assert args[1:] == (1000, 2000, ["dp"], 50)

    async def test_null_tags_returns_empty_list(self, mock_pg_conn):
        mock_pg_conn.fetch.return_value = [
            {
                "problem_id": "1A",
                "contest_id": "1",
                "name": "Test",
                "rating": None,
                "tags": None,
                "url": None,
            }
        ]

        result = await get_problems()

        assert result[0].tags == []


class TestGetProblemText:
    async def test_found_returns_dict(self, mock_pg_conn):
        mock_pg_conn.fetchrow.return_value = {
            "problem_id": "1A",
            "name": "Test",
            "text": "Statement content",
        }

        result = await get_problem_text("1A", "statement")

        assert result == {
            "problem_id": "1A",
            "name": "Test",
            "text": "Statement content",
        }

    async def test_not_found_returns_none(self, mock_pg_conn):
        mock_pg_conn.fetchrow.return_value = None

        result = await get_problem_text("999Z", "statement")

        assert result is None

    async def test_invalid_field_returns_none(self):
        result = await get_problem_text("1A", "invalid_field")

        assert result is None


class TestQdrantUpsertChunks:
    def test_calls_upsert_with_correct_collection(self, mock_qdrant_client, sample_chunk):
        qdrant_upsert_chunks([sample_chunk], [[0.1, 0.2]])

        call_kwargs = mock_qdrant_client.upsert.call_args.kwargs
        assert call_kwargs["collection_name"] == COLLECTION
        assert len(call_kwargs["points"]) == 1

    def test_truncates_payload_text_to_500_chars(self, mock_qdrant_client):
        chunk = Chunk(
            problem_id="1A",
            name="Test",
            chunk_type="statement",
            text="a" * 1000,
        )

        qdrant_upsert_chunks([chunk], [[0.1]])

        point = mock_qdrant_client.upsert.call_args.kwargs["points"][0]
        assert len(point.payload["text"]) == 500

    def test_preserves_metadata_in_payload(self, mock_qdrant_client, sample_chunk):
        qdrant_upsert_chunks([sample_chunk], [[0.1]])

        point = mock_qdrant_client.upsert.call_args.kwargs["points"][0]
        assert point.payload["problem_id"] == sample_chunk.problem_id
        assert point.payload["name"] == sample_chunk.name
        assert point.payload["rating"] == sample_chunk.rating
        assert point.payload["tags"] == sample_chunk.tags
        assert point.payload["chunk_type"] == sample_chunk.chunk_type


class TestQdrantSearch:
    def _make_mock_point(self, **overrides):
        defaults = {
            "problem_id": "1A",
            "name": "Test Problem",
            "rating": 1500,
            "tags": ["dp"],
            "chunk_type": "statement",
            "text": "snippet text",
        }
        defaults.update(overrides)
        point = MagicMock()
        point.score = overrides.get("score", 0.95)
        point.payload = {k: v for k, v in defaults.items() if k != "score"}
        return point

    def test_no_filters_returns_results(self, mock_qdrant_client):
        mock_point = self._make_mock_point()
        mock_qdrant_client.query_points.return_value = MagicMock(points=[mock_point])

        results = qdrant_search(vector=[0.1, 0.2])

        assert len(results) == 1
        assert results[0]["problem_id"] == "1A"
        assert results[0]["score"] == 0.95
        assert results[0]["snippet"] == "snippet text"

    def test_with_all_filters_passes_filter_object(self, mock_qdrant_client):
        mock_qdrant_client.query_points.return_value = MagicMock(points=[])

        qdrant_search(
            vector=[0.1],
            rating_min=1000,
            rating_max=2000,
            tags=["dp"],
            chunk_type="statement",
        )

        q_filter = mock_qdrant_client.query_points.call_args.kwargs["query_filter"]
        assert q_filter is not None
        assert len(q_filter.must) == 3

    def test_no_filters_passes_none_filter(self, mock_qdrant_client):
        mock_qdrant_client.query_points.return_value = MagicMock(points=[])

        qdrant_search(vector=[0.1])

        q_filter = mock_qdrant_client.query_points.call_args.kwargs["query_filter"]
        assert q_filter is None

    def test_skips_points_with_null_payload(self, mock_qdrant_client):
        mock_point = MagicMock()
        mock_point.payload = None
        mock_qdrant_client.query_points.return_value = MagicMock(points=[mock_point])

        results = qdrant_search(vector=[0.1])

        assert results == []

    def test_respects_limit_parameter(self, mock_qdrant_client):
        mock_qdrant_client.query_points.return_value = MagicMock(points=[])

        qdrant_search(vector=[0.1], limit=5)

        assert mock_qdrant_client.query_points.call_args.kwargs["limit"] == 5
