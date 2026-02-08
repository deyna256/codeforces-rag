"""Editorial segmentation benchmark runner using promptum."""

from loguru import logger
from promptum import Benchmark, OpenRouterClient, Report, RetryConfig, TestCase

from benchmarks.config import MAX_CONCURRENT, ModelConfig
from benchmarks.editorial_segmentation.test_data import SEGMENTATION_TEST_CASES
from benchmarks.validators import ProblemSegmentationValidator
from infrastructure.http_client import AsyncHTTPClient
from infrastructure.parsers.editorial_content_parser import EditorialContentParser

# System prompt copied from EditorialContentParser._ask_llm_for_segmentation
SEGMENTATION_SYSTEM_PROMPT = r"""You are an expert at analyzing Codeforces contest editorials.
Your task is to identify where each problem's solution starts and ends in the editorial text.

CRITICAL INSTRUCTIONS:
1. Editorials often cover MULTIPLE contests (e.g., Div1 + Div2) in ONE blog post.
   You MUST identify the contest ID for each problem to avoid confusion.

2. DO NOT extract or copy the full text - only identify boundaries!
   For each problem, find:
   - A unique text marker that indicates where the problem's solution STARTS
   - A unique text marker that indicates where the problem's solution ENDS

   These markers should be actual text from the editorial (e.g., "Problem A", "2189A", "Solution for A", etc.)

3. Return ONLY metadata about problem locations, not the full text content.

Return this JSON format:
{
  "problems": [
    {
      "contest_id": "1900",
      "problem_id": "A",
      "start_marker": "Problem A",
      "end_marker": "Problem B"
    },
    {
      "contest_id": "1900",
      "problem_id": "B",
      "start_marker": "Problem B",
      "end_marker": "Problem C"
    }
  ]
}

Guidelines:
- Look for contest IDs in: problem headers (e.g., "1900A"), section titles, blog text
- Use uppercase letters for problem_id (A, B, C, etc.)
- contest_id should be numeric string (e.g., "1900", "1901")
- start_marker and end_marker should be unique text snippets (10-50 characters) that appear in the editorial
- For the last problem, end_marker can be empty string "" if no clear ending
- If contest ID is ambiguous, infer from context or use the primary contest ID
- Return valid JSON only, no extra text"""

SEGMENTATION_USER_PROMPT_TEMPLATE = """Contest ID: {contest_id}

Expected problems: {expected_problems}

Full editorial text:
{editorial_text}

IMPORTANT: Identify the START and END markers for each problem's solution.
Find unique text snippets that mark where each problem begins and ends.
Do NOT copy the full text - only return the boundary markers.

Return JSON with contest_id, problem_id, start_marker, and end_marker for each problem."""

MAX_CHARS = 300_000


def _format_expected_problems(expected_problems: list[tuple[str, str]]) -> str:
    if not expected_problems:
        return "Unknown (parse all problems found)"
    return ", ".join(f"{cid}/{pid}" for cid, pid in expected_problems)


async def _prepare_segmentation_cases(
    model_config: ModelConfig,
) -> list[TestCase]:
    """Fetch editorial content and build promptum TestCase objects."""
    http_client = AsyncHTTPClient(timeout=30)
    # Use EditorialContentParser only for content extraction (no LLM client)
    parser = EditorialContentParser(http_client=http_client, llm_client=None)
    cases: list[TestCase] = []

    try:
        for tc in SEGMENTATION_TEST_CASES:
            contest_id = tc["contest_id"]
            editorial_urls = tc["editorial_urls"]
            expected_problems = tc["expected_problems"]

            # Skip test cases with no editorial URLs (no LLM call needed)
            if not editorial_urls:
                logger.debug(f"Skipping contest {contest_id} (no editorial URLs)")
                continue

            # Fetch and extract editorial content
            all_content: list[str] = []
            for url in editorial_urls:
                try:
                    content = await parser._fetch_editorial_content(url)
                    all_content.append(content)
                except Exception as e:
                    logger.warning(f"Failed to fetch editorial from {url}: {e}")

            if not all_content:
                logger.warning(f"No content fetched for contest {contest_id}, skipping")
                continue

            combined = await parser._combine_editorial_content(all_content)

            # Truncate if necessary
            if len(combined) > MAX_CHARS:
                combined = combined[:MAX_CHARS] + "\n\n[CONTENT TRUNCATED DUE TO LENGTH]"
                logger.warning(f"Truncated editorial text for contest {contest_id}")

            # Build expected problems list for prompt
            expected_list = list(expected_problems.keys())
            formatted = _format_expected_problems(expected_list)

            user_prompt = SEGMENTATION_USER_PROMPT_TEMPLATE.format(
                contest_id=contest_id,
                expected_problems=formatted,
                editorial_text=combined,
            )

            # Build validator
            validator = ProblemSegmentationValidator(
                expected_problems=tuple(
                    (cid, pid, should_exist)
                    for (cid, pid), should_exist in expected_problems.items()
                ),
            )

            cases.append(
                TestCase(
                    name=f"contest_{contest_id}",
                    prompt=user_prompt,
                    model=model_config["name"],
                    validator=validator,
                    system_prompt=SEGMENTATION_SYSTEM_PROMPT,
                    temperature=0.0,
                    max_tokens=model_config["max_tokens_segmentation"],
                    retry_config=RetryConfig(
                        max_attempts=2,
                        timeout=model_config["timeout_segmentation"],
                    ),
                    metadata={
                        "contest_id": contest_id,
                        "description": tc["description"],
                        "difficulty": tc["difficulty"],
                    },
                )
            )
    finally:
        await http_client.close()

    return cases


async def run_segmentation_benchmark(
    client: OpenRouterClient,
    model_config: ModelConfig,
) -> Report:
    """Run editorial segmentation benchmark for a single model.

    Args:
        client: Initialized promptum OpenRouterClient (context manager already entered)
        model_config: Model configuration

    Returns:
        promptum Report with results
    """
    logger.info(f"Preparing segmentation test cases for {model_config['display_name']}...")
    cases = await _prepare_segmentation_cases(model_config)
    logger.info(f"Prepared {len(cases)} test cases")

    def on_progress(completed: int, total: int, _result) -> None:
        logger.info(f"Segmentation progress: {completed}/{total}")

    benchmark = Benchmark(
        provider=client,
        name=f"segmentation_{model_config['name']}",
        max_concurrent=MAX_CONCURRENT,
        progress_callback=on_progress,
    )
    benchmark.add_tests(cases)
    return await benchmark.run_async()
