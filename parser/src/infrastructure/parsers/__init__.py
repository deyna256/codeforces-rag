"""Parsers for extracting data from external sources."""

from .contest_page_parser import ContestPageParser
from .editorial_content_parser import EditorialContentParser
from .llm_editorial_finder import LLMEditorialFinder
from .problem_page_parser import ProblemPageParser
from .url_parser import URLParser, URLParsingError
from .interfaces import (
    APIClientProtocol,
    ContestAPIClientProtocol,
    ContestPageParserProtocol,
    ParsingError,
    ProblemPageParserProtocol,
    URLParserProtocol,
)

__all__ = [
    "APIClientProtocol",
    "ContestAPIClientProtocol",
    "ContestPageParser",
    "ContestPageParserProtocol",
    "EditorialContentParser",
    "LLMEditorialFinder",
    "ParsingError",
    "ProblemPageParser",
    "ProblemPageParserProtocol",
    "URLParser",
    "URLParserProtocol",
    "URLParsingError",
]
