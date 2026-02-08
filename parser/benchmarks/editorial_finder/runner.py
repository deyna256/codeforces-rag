"""Editorial finder benchmark runner using promptum."""

from bs4 import BeautifulSoup
from loguru import logger
from promptum import Benchmark, OpenRouterClient, Report, RetryConfig, TestCase

from benchmarks.config import MAX_CONCURRENT, ModelConfig
from benchmarks.editorial_finder.test_data import FINDER_TEST_CASES
from benchmarks.validators import EditorialURLValidator
from infrastructure.http_client import AsyncHTTPClient
from infrastructure.parsers.llm_editorial_finder import LLMEditorialFinder

# System prompt copied from LLMEditorialFinder._ask_llm_for_editorial
FINDER_SYSTEM_PROMPT = """You are an expert at analyzing Codeforces contest pages.
Your task is to identify ALL links that lead to editorials/tutorials for the contest.

IMPORTANT: Some contests may have multiple editorial links (e.g., different divisions, multiple parts, alternative solutions). You must return ALL editorial links found.

Editorial/Solution links typically:
- Have text like "Tutorial", "Editorial", "Analysis", "Solutions", "Разбор задач", "Разбор" (Russian for "analysis", "solutions")
- Do NOT have text like "Announcement", "Registration", "Rules", "Timetable", or other meta-contest information
- Point to /blog/entry/ URLs
- Are posted by contest authors or coordinators
- Are typically posted AFTER the contest ends (not as announcements before)

Common editorial patterns:
- "Tutorial", "Editorial", "Analysis", "Solutions"
- "Разбор задач", "Разбор", "Решения" (Russian)
- Task-specific editorials: "Tutorial for A+B+C" etc.

Common non-editorial patterns to AVOID:
- "Announcement", "Registration", "Rules", "Problems", "Results"
- "Цуцсивцив", "Объявление", "Регистрация" (Russian)

Respond ONLY with a JSON object in this format:
{"urls": ["url1", "url2", ...]} if found, or {"urls": []} if no editorial links exist.

Examples:
- Single editorial: {"urls": ["https://codeforces.com/blog/entry/12345"]}
- Multiple editorials: {"urls": ["https://codeforces.com/blog/entry/12345", "https://codeforces.com/blog/entry/12346"]}
- No editorial: {"urls": []}

Do not include any explanation or additional text."""

FINDER_USER_PROMPT_TEMPLATE = """Contest ID: {contest_id}

Available links:
{links_text}

Which links are editorials/tutorials? Return ALL editorial links if multiple exist. Respond with JSON only."""


async def _prepare_finder_cases(
    model_config: ModelConfig,
) -> list[TestCase]:
    """Fetch contest pages and build promptum TestCase objects."""
    html_cache: dict[str, str] = {}
    http_client = AsyncHTTPClient(timeout=30)
    # Use LLMEditorialFinder only for HTML parsing (no LLM client needed)
    finder = LLMEditorialFinder(llm_client=None)
    cases: list[TestCase] = []

    try:
        for tc in FINDER_TEST_CASES:
            contest_id = tc["contest_id"]

            # Fetch HTML with caching
            if contest_id not in html_cache:
                url = f"https://codeforces.com/contest/{contest_id}"
                logger.debug(f"Fetching HTML for contest {contest_id}")
                html_cache[contest_id] = await http_client.get_text(url)

            html = html_cache[contest_id]
            soup = BeautifulSoup(html, "lxml")

            # Extract links using parser infrastructure
            links = finder._extract_links(soup)

            if not links:
                logger.debug(f"No links found for contest {contest_id}, skipping")
                continue

            # Build prompt
            links_text = "\n".join(
                f"{i + 1}. [{link['text']}] - {link['url']}" for i, link in enumerate(links)
            )
            user_prompt = FINDER_USER_PROMPT_TEMPLATE.format(
                contest_id=contest_id,
                links_text=links_text,
            )

            # Build validator
            validator = EditorialURLValidator(
                expected_urls=tuple(tc["expected_editorial"]),
            )

            cases.append(
                TestCase(
                    name=f"contest_{contest_id}",
                    prompt=user_prompt,
                    model=model_config["name"],
                    validator=validator,
                    system_prompt=FINDER_SYSTEM_PROMPT,
                    temperature=0.0,
                    max_tokens=model_config["max_tokens"],
                    retry_config=RetryConfig(
                        max_attempts=2,
                        timeout=model_config["timeout"],
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


async def run_finder_benchmark(
    client: OpenRouterClient,
    model_config: ModelConfig,
) -> Report:
    """Run editorial finder benchmark for a single model.

    Args:
        client: Initialized promptum OpenRouterClient (context manager already entered)
        model_config: Model configuration

    Returns:
        promptum Report with results
    """
    logger.info(f"Preparing finder test cases for {model_config['display_name']}...")
    cases = await _prepare_finder_cases(model_config)
    logger.info(f"Prepared {len(cases)} test cases")

    def on_progress(completed: int, total: int, _result) -> None:
        logger.info(f"Finder progress: {completed}/{total}")

    benchmark = Benchmark(
        provider=client,
        name=f"finder_{model_config['name']}",
        max_concurrent=MAX_CONCURRENT,
        progress_callback=on_progress,
    )
    benchmark.add_tests(cases)
    return await benchmark.run_async()
