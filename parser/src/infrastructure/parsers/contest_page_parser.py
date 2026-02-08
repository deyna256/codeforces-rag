"""Parser for extracting contest data from HTML pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from loguru import logger

from domain.models.parsing import ContestPageData, ProblemData

from .interfaces import ParsingError
from .llm_editorial_finder import LLMEditorialFinder
from .html_utils import extract_time_limit, extract_memory_limit, extract_description

if TYPE_CHECKING:
    from infrastructure.http_client import AsyncHTTPClient


class ContestPageParser:
    """Parser for extracting data from Codeforces contest HTML pages."""

    def __init__(
        self,
        http_client: AsyncHTTPClient | None = None,
        llm_editorial_finder: LLMEditorialFinder | None = None,
    ):
        """
        Initialize parser.

        Args:
            http_client: Async HTTP client instance
            llm_editorial_finder: LLM-based editorial finder (optional)
        """
        self.http_client = http_client
        self.llm_editorial_finder = llm_editorial_finder

    async def parse_contest_page(self, contest_id: str) -> ContestPageData:
        """
        Parse contest page and extract data (editorial URL).
        """
        from infrastructure.parsers import URLParser
        from domain.models.identifiers import ContestIdentifier

        url = URLParser.build_contest_url(ContestIdentifier(contest_id=contest_id))

        if not self.http_client:
            raise ParsingError(f"HTTP client not initialized for {url}")

        try:
            html = await self.http_client.get_text(url)
            soup = BeautifulSoup(html, "lxml")

            editorial_urls = await self._extract_editorial_url(soup, contest_id)

            contest_data = ContestPageData(
                contest_id=contest_id,
                editorial_urls=editorial_urls,
            )

            return contest_data

        except Exception as e:
            raise ParsingError(f"Failed to parse contest page {url}: {e}") from e

    async def parse_problem_in_contest(self, contest_id: str, problem_id: str) -> ProblemData:
        """
        Parse problem page within a contest and extract data.
        """
        url = f"https://codeforces.com/contest/{contest_id}/problem/{problem_id}"

        if not self.http_client:
            raise ParsingError(f"HTTP client not initialized for {url}")

        try:
            html = await self.http_client.get_text(url)
            soup = BeautifulSoup(html, "lxml")

            # Extract data using shared HTML parsing utilities
            description = extract_description(soup)
            time_limit = extract_time_limit(soup)
            memory_limit = extract_memory_limit(soup)

            problem_data = ProblemData(
                description=description,
                time_limit=time_limit,
                memory_limit=memory_limit,
            )

            return problem_data

        except Exception as e:
            raise ParsingError(f"Failed to parse problem page {url}: {e}") from e

    async def _extract_editorial_url(self, soup: BeautifulSoup, contest_id: str) -> list[str]:
        """Extract editorial/tutorial URLs from contest page using LLM."""
        if not self.llm_editorial_finder:
            logger.warning(f"No LLM editorial finder available for contest {contest_id}")
            return []

        try:
            return await self.llm_editorial_finder.find_editorial_url(soup, contest_id)
        except Exception:
            logger.exception(f"Error extracting editorial URLs for contest {contest_id}")
            return []
