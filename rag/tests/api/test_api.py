import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.models import ProblemListItem


class TestHealth:
    def test_all_services_healthy(self, client):
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_qdrant = MagicMock()
        mock_qdrant.get_collection.return_value = MagicMock(points_count=42)

        with (
            patch("src.api.db.pg_pool", mock_pool),
            patch("src.api.db.qdrant", mock_qdrant),
        ):
            response = client.get("/health")

        data = response.json()
        assert response.status_code == 200
        assert data["status"] == "ok"
        assert data["postgres"] is True
        assert data["qdrant"] is True
        assert data["qdrant_points"] == 42

    def test_degraded_when_services_unavailable(self, client):
        with (
            patch("src.api.db.pg_pool", None),
            patch("src.api.db.qdrant", None),
        ):
            response = client.get("/health")

        data = response.json()
        assert data["status"] == "degraded"
        assert data["postgres"] is False
        assert data["qdrant"] is False


class TestLoadedContests:
    def test_returns_loaded_contest_ids(self, client):
        with patch(
            "src.api.db.get_loaded_contest_ids",
            new_callable=AsyncMock,
            return_value=["1920", "1921"],
        ):
            response = client.get("/contests/loaded")

        data = response.json()
        assert response.status_code == 200
        assert data == ["1920", "1921"]

    def test_returns_empty_list(self, client):
        with patch(
            "src.api.db.get_loaded_contest_ids",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/contests/loaded")

        assert response.status_code == 200
        assert response.json() == []


class TestLoadContest:
    def test_success_returns_contest_info(self, client):
        mock_resp = MagicMock()
        mock_resp.title = "Codeforces Round 920"

        with (
            patch(
                "src.api.fetch_contest",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            patch(
                "src.api.index_contest",
                new_callable=AsyncMock,
                return_value=3,
            ),
        ):
            response = client.post(
                "/contests/load",
                json={"contest_url": "https://codeforces.com/contest/1920"},
            )

        data = response.json()
        assert response.status_code == 200
        assert data["contest"] == "Codeforces Round 920"
        assert data["problems_loaded"] == 3

    def test_fetch_contest_error_propagates(self, client):
        with patch(
            "src.api.fetch_contest",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                client.post(
                    "/contests/load",
                    json={"contest_url": "https://codeforces.com/contest/9999"},
                )


class TestSearch:
    def test_returns_search_results(self, client):
        hits = [
            {
                "problem_id": "1920A",
                "name": "Test Problem",
                "rating": 1500,
                "tags": ["dp"],
                "score": 0.9,
                "snippet": "sample text",
            }
        ]

        with (
            patch("src.api.embed_texts", return_value=[[0.1, 0.2]]),
            patch("src.api.db.qdrant_search", return_value=hits),
        ):
            response = client.post("/search", json={"query": "dp problems"})

        data = response.json()
        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["problem_id"] == "1920A"
        assert data[0]["score"] == 0.9

    def test_passes_filters_to_search(self, client):
        with (
            patch("src.api.embed_texts", return_value=[[0.1]]),
            patch("src.api.db.qdrant_search", return_value=[]) as mock_search,
        ):
            response = client.post(
                "/search",
                json={
                    "query": "dp",
                    "rating_min": 1000,
                    "rating_max": 2000,
                    "tags": ["dp"],
                    "chunk_type": "editorial",
                    "limit": 5,
                },
            )

        assert response.status_code == 200
        assert response.json() == []
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["rating_min"] == 1000
        assert call_kwargs["rating_max"] == 2000
        assert call_kwargs["tags"] == ["dp"]
        assert call_kwargs["chunk_type"] == "editorial"
        assert call_kwargs["limit"] == 5

    def test_embedding_failure_propagates(self, client):
        with patch("src.api.embed_texts", side_effect=RuntimeError("OpenAI unavailable")):
            with pytest.raises(RuntimeError):
                client.post("/search", json={"query": "dp problems"})


class TestListProblems:
    def test_returns_problem_list(self, client):
        items = [
            ProblemListItem(
                problem_id="1920A",
                contest_id="1920",
                name="Test",
                rating=1500,
                tags=["dp"],
            )
        ]

        with patch(
            "src.api.db.get_problems",
            new_callable=AsyncMock,
            return_value=items,
        ):
            response = client.get("/problems")

        data = response.json()
        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["problem_id"] == "1920A"

    def test_passes_query_params(self, client):
        with patch(
            "src.api.db.get_problems",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get:
            response = client.get(
                "/problems",
                params={
                    "rating_min": 1000,
                    "contest_id": "1920",
                    "limit": 10,
                },
            )

        assert response.status_code == 200
        assert response.json() == []
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["rating_min"] == 1000
        assert call_kwargs["contest_id"] == "1920"
        assert call_kwargs["limit"] == 10


@pytest.mark.parametrize(
    "path",
    [
        "/problems/1920A/statement",
        "/problems/1920A/editorial",
    ],
)
class TestProblemText:
    def test_found_returns_text(self, client, path):
        result = {
            "problem_id": "1920A",
            "name": "Test",
            "text": "Content",
        }

        with patch(
            "src.api.db.get_problem_text",
            new_callable=AsyncMock,
            return_value=result,
        ):
            response = client.get(path)

        data = response.json()
        assert response.status_code == 200
        assert data["text"] == "Content"

    def test_not_found_returns_404(self, client, path):
        not_found_path = path.replace("1920A", "999Z")

        with patch(
            "src.api.db.get_problem_text",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.get(not_found_path)

        assert response.status_code == 404
