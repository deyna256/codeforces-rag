"""Value objects for parsed data."""

from dataclasses import dataclass, field


@dataclass
class ProblemData:
    """Data extracted from a problem page."""

    description: str | None = None
    time_limit: str | None = None
    memory_limit: str | None = None


@dataclass
class ContestPageData:
    """Data extracted from a contest page."""

    contest_id: str
    editorial_urls: list[str] = field(default_factory=list)
