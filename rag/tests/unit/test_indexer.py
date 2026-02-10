from unittest.mock import AsyncMock, MagicMock, patch

from src.indexer import index_contest
from src.models import ParserProblem, ParserResponse


class TestIndexContest:
    async def test_processes_all_problems_and_indexes(self, sample_parser_response):
        with (
            patch("src.indexer.upsert_problem", new_callable=AsyncMock) as mock_upsert,
            patch("src.indexer.chunk_problem") as mock_chunk,
            patch("src.indexer.embed_texts") as mock_embed,
            patch("src.indexer.qdrant_upsert_chunks") as mock_qdrant,
        ):
            mock_chunk.return_value = [MagicMock(text="chunk")]
            mock_embed.return_value = [[0.1]]

            count = await index_contest(sample_parser_response)

        assert count == 1
        mock_upsert.assert_awaited_once()
        mock_embed.assert_called_once()
        mock_qdrant.assert_called_once()

    async def test_constructs_problem_id_and_url(self, sample_parser_response):
        with (
            patch("src.indexer.upsert_problem", new_callable=AsyncMock) as mock_upsert,
            patch("src.indexer.chunk_problem", return_value=[]),
            patch("src.indexer.embed_texts"),
            patch("src.indexer.qdrant_upsert_chunks"),
        ):
            await index_contest(sample_parser_response)

        problem = mock_upsert.call_args[0][0]
        assert problem.problem_id == "1920A"
        assert problem.url == "https://codeforces.com/contest/1920/problem/A"

    async def test_maps_explanation_to_editorial(self, sample_parser_response):
        with (
            patch("src.indexer.upsert_problem", new_callable=AsyncMock) as mock_upsert,
            patch("src.indexer.chunk_problem", return_value=[]),
            patch("src.indexer.embed_texts"),
            patch("src.indexer.qdrant_upsert_chunks"),
        ):
            await index_contest(sample_parser_response)

        problem = mock_upsert.call_args[0][0]
        assert problem.editorial == "Sort the constraints and check the range."

    async def test_empty_problems_skips_embedding(self):
        response = ParserResponse(contest_id="1", title="Empty", problems=[])

        with (
            patch("src.indexer.embed_texts") as mock_embed,
            patch("src.indexer.qdrant_upsert_chunks") as mock_qdrant,
        ):
            count = await index_contest(response)

        assert count == 0
        mock_embed.assert_not_called()
        mock_qdrant.assert_not_called()

    async def test_no_chunks_skips_embedding(self):
        pp = ParserProblem(
            contest_id="1", id="A", title="No Content",
            statement="", explanation=None,
        )
        response = ParserResponse(contest_id="1", title="Test", problems=[pp])

        with (
            patch("src.indexer.upsert_problem", new_callable=AsyncMock),
            patch("src.indexer.chunk_problem", return_value=[]),
            patch("src.indexer.embed_texts") as mock_embed,
            patch("src.indexer.qdrant_upsert_chunks") as mock_qdrant,
        ):
            await index_contest(response)

        mock_embed.assert_not_called()
        mock_qdrant.assert_not_called()
