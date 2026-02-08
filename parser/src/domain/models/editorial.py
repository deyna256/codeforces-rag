from dataclasses import dataclass


@dataclass
class Editorial:
    """Editorial analysis for a specific problem."""

    contest_id: str
    problem_id: str
    analysis_text: str


@dataclass
class ContestEditorial:
    """Complete editorial with all problem analyses for a contest."""

    contest_id: str
    editorials: list[Editorial]
