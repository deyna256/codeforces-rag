"""Generate JSON comparison reports from promptum Reports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from promptum import Report


def generate_comparison_report(
    model_reports: dict[str, Report],
    display_names: dict[str, str],
    output_dir: Path,
    benchmark_type: str,
) -> tuple[Path, dict[str, Any]]:
    """Generate a comprehensive comparison report for all models.

    Args:
        model_reports: Mapping of model_name -> promptum Report
        display_names: Mapping of model_name -> human-readable display name
        output_dir: Directory to save the report
        benchmark_type: Type of benchmark ("editorial_finder" or "editorial_segmentation")

    Returns:
        Tuple of (report_path, report_data)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"benchmark_comparison_{timestamp}.json"

    # Determine total test cases from first report
    first_report = next(iter(model_reports.values()), None)
    total_tests = len(first_report.results) if first_report else 0

    report_data: dict[str, Any] = {
        "benchmark_info": {
            "type": benchmark_type,
            "timestamp": timestamp,
            "total_models": len(model_reports),
            "test_cases": total_tests,
        },
        "summary": [],
        "detailed_results": {},
    }

    for model_name, report in model_reports.items():
        summary = report.get_summary()
        display_name = display_names.get(model_name, model_name)

        # Calculate classification metrics from validation_details
        tp, fp, fn, tn = _calculate_classification(report, benchmark_type)
        precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        # Cost per correct prediction
        cost_per_correct = (summary.total_cost_usd / summary.passed) if summary.passed > 0 else 0.0

        # Token averages
        avg_tokens = summary.total_tokens / summary.total if summary.total > 0 else 0.0

        # Collect per-result prompt/completion tokens
        total_prompt = sum((r.metrics.prompt_tokens or 0) for r in report.results if r.metrics)
        total_completion = sum(
            (r.metrics.completion_tokens or 0) for r in report.results if r.metrics
        )

        model_summary = {
            "model_name": model_name,
            "display_name": display_name,
            "accuracy": round(summary.pass_rate * 100, 2),
            "successful_tests": summary.passed,
            "failed_tests": summary.failed,
            "avg_latency_ms": round(summary.avg_latency_ms, 2),
            "avg_tokens_per_test": round(avg_tokens, 2),
            "total_tokens": summary.total_tokens,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "estimated_cost_usd": round(summary.total_cost_usd, 4),
            "cost_per_correct_prediction_usd": round(cost_per_correct, 4),
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "f1_score": round(f1, 2),
            "pricing": None,
        }
        report_data["summary"].append(model_summary)

        # Detailed per-test results
        test_results = []
        for r in report.results:
            contest_id = r.test_case.metadata.get("contest_id", "")
            details = r.validation_details
            latency = r.metrics.latency_ms if r.metrics else 0.0
            prompt_tokens = (r.metrics.prompt_tokens or 0) if r.metrics else 0
            completion_tokens = (r.metrics.completion_tokens or 0) if r.metrics else 0
            total_tokens = (r.metrics.total_tokens or 0) if r.metrics else 0

            if benchmark_type == "editorial_finder":
                test_results.append(
                    {
                        "contest_id": contest_id,
                        "expected": details.get("expected", []),
                        "found": details.get("found", []),
                        "correct": r.passed,
                        "latency_ms": round(latency, 2),
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "error": r.execution_error,
                    }
                )
            else:
                test_results.append(
                    {
                        "contest_id": contest_id,
                        "expected_problems": details.get("expected_problems", []),
                        "found_problems": details.get("found_problems", []),
                        "problem_accuracy": details.get("problem_accuracy", {}),
                        "correct": r.passed,
                        "latency_ms": round(latency, 2),
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "error": r.execution_error,
                    }
                )

        report_data["detailed_results"][model_name] = {"test_results": test_results}

    # Sort summary by accuracy desc, then cost per correct prediction asc
    report_data["summary"].sort(
        key=lambda x: (-x["accuracy"], x.get("cost_per_correct_prediction_usd", 1e9))
    )

    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)

    return report_path, report_data


def _calculate_classification(report: Report, benchmark_type: str) -> tuple[int, int, int, int]:
    """Calculate TP, FP, FN, TN from validation details."""
    tp = fp = fn = tn = 0

    for r in report.results:
        if r.execution_error:
            continue

        details = r.validation_details

        if benchmark_type == "editorial_finder":
            expected = details.get("expected", [])
            found = details.get("found", [])
            has_expected = len(expected) > 0
            has_found = len(found) > 0

            if has_expected and has_found and r.passed:
                tp += 1
            elif not has_expected and has_found:
                fp += 1
            elif has_expected and not has_found:
                fn += 1
            elif not has_expected and not has_found:
                tn += 1
        else:
            # Segmentation: count per-problem
            accuracy = details.get("problem_accuracy", {})
            expected_problems = details.get("expected_problems", [])
            found_problems = details.get("found_problems", [])

            for key, was_correct in accuracy.items():
                is_expected = key in expected_problems
                is_found = key in found_problems

                if is_expected and is_found and was_correct:
                    tp += 1
                elif not is_expected and is_found:
                    fp += 1
                elif is_expected and not is_found:
                    fn += 1
                elif not is_expected and not is_found:
                    tn += 1

    return tp, fp, fn, tn
