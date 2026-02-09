"""Main benchmark runner for testing LLM models via promptum."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root and src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# ruff: noqa: E402
from dotenv import load_dotenv
from loguru import logger
from promptum import OpenRouterClient, Report

from benchmarks.config import MODELS_TO_BENCHMARK
from benchmarks.editorial_finder.runner import run_finder_benchmark
from benchmarks.editorial_segmentation.runner import run_segmentation_benchmark
from benchmarks.reporting import (
    generate_comparison_report,
    generate_html_report,
    print_comparison_table,
)


async def main():
    """Main entry point for benchmark script."""
    load_dotenv()

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    assert api_key is not None

    parser = argparse.ArgumentParser(description="Run LLM benchmarks")
    parser.add_argument("--all", action="store_true", help="Run all models")
    parser.add_argument("--model", type=str, help="Filter models by name")
    parser.add_argument(
        "--type",
        type=str,
        choices=["finder", "segmentation", "all"],
        default="all",
        help="Benchmark type to run (default: all)",
    )

    args = parser.parse_args()

    # Determine benchmark types to run
    benchmark_types: list[str] = []
    if args.type in ["finder", "all"]:
        benchmark_types.append("editorial_finder")
    if args.type in ["segmentation", "all"]:
        benchmark_types.append("editorial_segmentation")

    # Determine which models to run
    models_to_run = MODELS_TO_BENCHMARK
    if args.model and not args.all:
        models_to_run = [m for m in MODELS_TO_BENCHMARK if args.model in m["name"]]
        if not models_to_run:
            logger.error(f"No models found matching: {args.model}")
            sys.exit(1)

    # Build display names mapping
    display_names = {m["name"]: m["display_name"] for m in models_to_run}

    for benchmark_type in benchmark_types:
        logger.info("=" * 80)
        logger.info(f"Running {benchmark_type} benchmark")
        logger.info("=" * 80)

        if benchmark_type == "editorial_finder":
            results_dir = Path(__file__).parent / "results" / "editorial_finder"
        else:
            results_dir = Path(__file__).parent / "results" / "editorial_segmentation"

        logger.info(f"Running benchmarks for {len(models_to_run)} model(s)")

        model_reports: dict[str, Report] = {}

        for model_config in models_to_run:
            model_name = model_config["name"]
            try:
                async with OpenRouterClient(api_key=api_key) as client:
                    if benchmark_type == "editorial_finder":
                        report = await run_finder_benchmark(client, model_config)
                    else:
                        report = await run_segmentation_benchmark(client, model_config)

                model_reports[model_name] = report

                summary = report.get_summary()
                logger.info(
                    f"{model_config['display_name']}: "
                    f"pass_rate={summary.pass_rate:.1%}, "
                    f"latency={summary.avg_latency_ms:.0f}ms, "
                    f"tokens={summary.total_tokens}, "
                    f"cost=${summary.total_cost_usd:.6f}"
                )

            except Exception as e:
                logger.error(f"Failed to benchmark {model_config['display_name']}: {e}")

        if model_reports:
            logger.info("Generating reports...")

            # Generate JSON report
            json_path, report_data = generate_comparison_report(
                model_reports,
                display_names,
                results_dir,
                benchmark_type,
            )
            logger.info(f"Saved JSON report: {json_path}")

            # Generate HTML report
            timestamp = report_data["benchmark_info"]["timestamp"]
            html_path = results_dir / f"benchmark_report_{timestamp}.html"
            html_path = generate_html_report(report_data, html_path)
            logger.info(f"Saved HTML report: {html_path}")

            # Print console table
            if len(model_reports) > 1:
                print_comparison_table(model_reports, display_names)

            print(f"\nView report in browser: file://{html_path.absolute()}\n")

    logger.info("Benchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())
