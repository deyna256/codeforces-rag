"""Custom promptum validators for benchmark test cases."""

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EditorialURLValidator:
    """Validates LLM response for editorial URL finding.

    Parses JSON {"urls": [...]} and compares against expected URLs.
    """

    expected_urls: tuple[str, ...]

    def validate(self, response: str) -> tuple[bool, dict[str, Any]]:
        try:
            result = json.loads(response)
            found = result.get("urls", [])
        except (json.JSONDecodeError, AttributeError):
            return False, {"expected": list(self.expected_urls), "found": [], "matched": []}

        expected_norm = {url.rstrip("/").lower() for url in self.expected_urls}
        found_norm = {url.rstrip("/").lower() for url in found}
        matched = list(expected_norm & found_norm)

        # No editorial expected and none found
        if not expected_norm and not found_norm:
            return True, {"expected": [], "found": [], "matched": []}

        # No editorial expected but some found
        if not expected_norm and found_norm:
            return False, {"expected": [], "found": found, "matched": []}

        # Editorial expected but none found
        if expected_norm and not found_norm:
            return False, {"expected": list(self.expected_urls), "found": [], "matched": []}

        # Both present — pass if any intersection
        passed = len(matched) > 0
        return passed, {
            "expected": list(self.expected_urls),
            "found": found,
            "matched": matched,
        }

    def describe(self) -> str:
        if not self.expected_urls:
            return "Expects no editorial URLs"
        return f"Expects editorial URLs: {', '.join(self.expected_urls)}"


@dataclass(frozen=True, slots=True)
class ProblemSegmentationValidator:
    """Validates LLM response for editorial segmentation.

    Parses JSON {"problems": [{"contest_id": ..., "problem_id": ...}, ...]}
    and checks that found problems match expected.

    expected_problems: tuple of (contest_id, problem_id, should_exist) triples.
    """

    expected_problems: tuple[tuple[str, str, bool], ...]

    def validate(self, response: str) -> tuple[bool, dict[str, Any]]:
        try:
            result = json.loads(response)
            problems = result.get("problems", [])
        except (json.JSONDecodeError, AttributeError):
            accuracy = {
                f"{cid}/{pid}": not should_exist
                for cid, pid, should_exist in self.expected_problems
            }
            return False, {
                "expected_problems": [
                    f"{cid}/{pid}" for cid, pid, _ in self.expected_problems
                ],
                "found_problems": [],
                "problem_accuracy": accuracy,
            }

        found_set: set[str] = set()
        found_list: list[str] = []
        for p in problems:
            if isinstance(p, dict):
                cid = str(p.get("contest_id", "")).strip()
                pid = str(p.get("problem_id", "")).strip().upper()
                if cid and pid:
                    key = f"{cid}/{pid}"
                    found_set.add(key)
                    found_list.append(key)

        accuracy: dict[str, bool] = {}
        for cid, pid, should_exist in self.expected_problems:
            key = f"{cid}/{pid}"
            accuracy[key] = (key in found_set) == should_exist

        passed = all(accuracy.values()) if accuracy else True
        return passed, {
            "expected_problems": [
                f"{cid}/{pid}" for cid, pid, _ in self.expected_problems
            ],
            "found_problems": found_list,
            "problem_accuracy": accuracy,
        }

    def describe(self) -> str:
        parts = [
            f"{cid}/{pid}={'present' if s else 'absent'}"
            for cid, pid, s in self.expected_problems
        ]
        return f"Expects problems: {', '.join(parts)}"
