"""Integration tests for API routes using Litestar TestClient."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from litestar.testing import TestClient

from domain.models.contest import Contest, ContestProblem
from domain.models.problem import Problem
from infrastructure.errors import ContestNotFoundError
from infrastructure.parsers import URLParsingError


@pytest.fixture
def mock_contest_service():
    return AsyncMock()


@pytest.fixture
def mock_problem_service():
    return AsyncMock()


@pytest.fixture
def client(mock_contest_service, mock_problem_service):
    settings = MagicMock()
    settings.log_level = "INFO"

    with (
        patch("api.routes.contest.create_contest_service", return_value=mock_contest_service),
        patch("api.routes.problem.create_problem_service", return_value=mock_problem_service),
        patch("config.get_settings", return_value=settings),
    ):
        from api.app import create_app

        app = create_app()
        with TestClient(app=app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# Contest routes
# ---------------------------------------------------------------------------


def test_post_contest_success_returns_200(client, mock_contest_service):
    contest = Contest(
        contest_id="1900",
        title="Test Round",
        problems=[
            ContestProblem(
                contest_id="1900",
                id="A",
                title="Problem A",
                tags=["math"],
                rating=800,
            )
        ],
        editorials=["https://codeforces.com/blog/entry/1"],
    )
    mock_contest_service.get_contest_by_url.return_value = contest

    response = client.post("/contest/", json={"url": "https://codeforces.com/contest/1900"})

    assert response.status_code == 200
    data = response.json()
    assert data["contest_id"] == "1900"
    assert len(data["problems"]) == 1
    assert data["problems"][0]["id"] == "A"


def test_post_contest_url_parsing_error_returns_400(client, mock_contest_service):
    mock_contest_service.get_contest_by_url.side_effect = URLParsingError("bad url")

    response = client.post("/contest/", json={"url": "invalid"})

    assert response.status_code == 400


def test_post_contest_not_found_returns_404(client, mock_contest_service):
    mock_contest_service.get_contest_by_url.side_effect = ContestNotFoundError("not found")

    response = client.post("/contest/", json={"url": "https://codeforces.com/contest/9999"})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Problem routes
# ---------------------------------------------------------------------------


def test_post_problem_success_returns_200(client, mock_problem_service):
    problem = Problem(
        contest_id="1900",
        id="A",
        statement="Test statement",
        rating=800,
        tags=["math"],
    )
    mock_problem_service.get_problem_by_url.return_value = problem

    response = client.post(
        "/problems/", json={"url": "https://codeforces.com/problemset/problem/1900/A"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["contest_id"] == "1900"
    assert data["id"] == "A"


def test_post_problem_url_parsing_error_returns_400(client, mock_problem_service):
    mock_problem_service.get_problem_by_url.side_effect = URLParsingError("bad url")

    response = client.post("/problems/", json={"url": "invalid"})

    assert response.status_code == 400
