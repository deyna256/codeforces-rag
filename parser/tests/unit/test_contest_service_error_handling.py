import pytest
from unittest.mock import MagicMock

from services.contest import ContestService


@pytest.mark.asyncio
async def test_continues_when_page_parser_fails(api_client, page_parser, editorial_parser):
    api_client.fetch_contest_standings.return_value = {
        "result": {
            "contest": {"name": "Contest 1000", "type": "CF"},
            "problems": [
                {"index": "A", "name": "Problem A", "rating": 800, "tags": ["math"]},
            ],
        }
    }

    page_parser.parse_contest_page.side_effect = Exception("Network error")
    page_parser.parse_problem_in_contest.return_value = MagicMock(
        description="Description", time_limit="1s", memory_limit="256MB"
    )

    service = ContestService(
        api_client=api_client, page_parser=page_parser, editorial_parser=editorial_parser
    )
    contest = await service.get_contest("1000")

    assert contest.contest_id == "1000"
    assert contest.title == "Contest 1000"
    assert len(contest.problems) == 1
    assert contest.editorials == []


@pytest.mark.asyncio
async def test_continues_when_problem_parsing_fails(api_client, page_parser, editorial_parser):
    api_client.fetch_contest_standings.return_value = {
        "result": {
            "contest": {"name": "Contest 2000", "type": "CF"},
            "problems": [
                {"index": "A", "name": "Problem A", "rating": 800, "tags": ["math"]},
                {"index": "B", "name": "Problem B", "rating": 1200, "tags": ["dp"]},
                {"index": "C", "name": "Problem C", "rating": 1600, "tags": ["graphs"]},
            ],
        }
    }

    page_parser.parse_contest_page.return_value = MagicMock(editorial_urls=[])
    page_parser.parse_problem_in_contest.side_effect = [
        MagicMock(description="Description A", time_limit="1s", memory_limit="256MB"),
        Exception("Failed to parse B"),
        MagicMock(description="Description C", time_limit="1s", memory_limit="256MB"),
    ]

    service = ContestService(
        api_client=api_client, page_parser=page_parser, editorial_parser=editorial_parser
    )
    contest = await service.get_contest("2000")

    assert len(contest.problems) == 3
    problem_b = next(p for p in contest.problems if p.id == "B")
    assert problem_b.statement is None


@pytest.mark.asyncio
async def test_get_contest_by_url_success(api_client, page_parser, editorial_parser, url_parser):
    identifier = MagicMock()
    identifier.contest_id = "1500"
    url_parser.parse_contest_url.return_value = identifier

    api_client.fetch_contest_standings.return_value = {
        "result": {
            "contest": {"name": "Contest 1500", "type": "CF"},
            "problems": [{"index": "A", "name": "Problem A", "rating": 800, "tags": ["math"]}],
        }
    }

    page_parser.parse_contest_page.return_value = MagicMock(editorial_urls=[])
    page_parser.parse_problem_in_contest.return_value = MagicMock(
        description="Description", time_limit="1s", memory_limit="256MB"
    )

    service = ContestService(
        api_client=api_client,
        page_parser=page_parser,
        url_parser=url_parser,  # type: ignore[arg-type]
        editorial_parser=editorial_parser,
    )
    contest = await service.get_contest_by_url("https://codeforces.com/contest/1500")

    assert contest.contest_id == "1500"
    assert contest.title == "Contest 1500"
    url_parser.parse_contest_url.assert_called_once_with("https://codeforces.com/contest/1500")


@pytest.mark.asyncio
async def test_continues_when_editorial_parsing_fails(api_client, page_parser, editorial_parser):
    api_client.fetch_contest_standings.return_value = {
        "result": {
            "contest": {"name": "Contest 5000", "type": "CF"},
            "problems": [{"index": "A", "name": "Problem A", "rating": 800, "tags": ["math"]}],
        }
    }

    page_parser.parse_contest_page.return_value = MagicMock(
        editorial_urls=["https://codeforces.com/blog/entry/12345"]
    )
    page_parser.parse_problem_in_contest.return_value = MagicMock(
        description="Description", time_limit="1s", memory_limit="256MB"
    )
    editorial_parser.parse_editorial_content.side_effect = Exception("Editorial parsing failed")

    service = ContestService(
        api_client=api_client, page_parser=page_parser, editorial_parser=editorial_parser
    )
    contest = await service.get_contest("5000")

    assert contest.contest_id == "5000"
    assert len(contest.problems) == 1
    assert contest.problems[0].explanation is None
