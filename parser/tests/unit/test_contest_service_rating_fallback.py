import pytest
from unittest.mock import MagicMock

from services.contest import ContestService


@pytest.mark.asyncio
async def test_uses_rating_from_standings_when_available(api_client, page_parser, editorial_parser):
    api_client.fetch_contest_standings.return_value = {
        "result": {
            "contest": {"name": "Contest 102", "type": "CF"},
            "problems": [
                {
                    "index": "A",
                    "name": "Problem A",
                    "rating": 1200,
                    "tags": ["brute force"],
                },
                {
                    "index": "D",
                    "name": "Problem D",
                    "rating": 1900,
                    "tags": ["dp", "graphs"],
                },
            ],
        }
    }

    page_parser.parse_contest_page.return_value = MagicMock(editorial_urls=[])
    page_parser.parse_problem_in_contest.return_value = MagicMock(
        description="Test description", time_limit="1 second", memory_limit="256 MB"
    )

    service = ContestService(
        api_client=api_client, page_parser=page_parser, editorial_parser=editorial_parser
    )
    contest = await service.get_contest("102")

    assert len(contest.problems) == 2
    problem_a = next(p for p in contest.problems if p.id == "A")
    problem_d = next(p for p in contest.problems if p.id == "D")
    assert problem_a.rating == 1200
    assert problem_a.tags == ["brute force"]
    assert problem_d.rating == 1900
    assert problem_d.tags == ["dp", "graphs"]


@pytest.mark.asyncio
async def test_handles_missing_rating_in_standings(api_client, page_parser, editorial_parser):
    api_client.fetch_contest_standings.return_value = {
        "result": {
            "contest": {"name": "Contest 888", "type": "CF"},
            "problems": [
                {
                    "index": "A",
                    "name": "Problem A",
                },
            ],
        }
    }
    page_parser.parse_contest_page.return_value = MagicMock(editorial_urls=[])
    page_parser.parse_problem_in_contest.return_value = MagicMock(
        description="Test description", time_limit="1 second", memory_limit="256 MB"
    )

    service = ContestService(
        api_client=api_client, page_parser=page_parser, editorial_parser=editorial_parser
    )
    contest = await service.get_contest("888")

    assert len(contest.problems) == 1
    problem_a = contest.problems[0]
    assert problem_a.rating is None
    assert problem_a.tags == []
