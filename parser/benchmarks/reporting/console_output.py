"""Console output formatting for benchmark results."""

from promptum import Report


def print_comparison_table(
    model_reports: dict[str, Report],
    display_names: dict[str, str],
) -> None:
    """Print a formatted comparison table to console.

    Args:
        model_reports: Mapping of model_name -> promptum Report
        display_names: Mapping of model_name -> human-readable display name
    """
    if not model_reports:
        return

    rows: list[tuple[str, float, float, float, int, float]] = []
    for model_name, report in model_reports.items():
        summary = report.get_summary()
        display = display_names.get(model_name, model_name)
        accuracy = summary.pass_rate * 100
        avg_tokens = summary.total_tokens / summary.total if summary.total > 0 else 0.0
        rows.append((
            display,
            accuracy,
            summary.avg_latency_ms,
            avg_tokens,
            summary.total_tokens,
            summary.total_cost_usd,
        ))

    # Sort by accuracy desc, then cost asc
    rows.sort(key=lambda r: (-r[1], r[5] if r[5] > 0 else 1e9))

    print("\n" + "=" * 120)
    print("BENCHMARK COMPARISON (Sorted: Accuracy -> Price)")
    print("=" * 120)
    print(
        f"{'Rank':<6} {'Model':<30} {'Accuracy':>10} {'Avg Latency':>13} "
        f"{'Avg Tokens':>12} {'Total Tokens':>14} {'Est. Cost':>12}"
    )
    print("-" * 120)

    for rank, (display, accuracy, latency, avg_tokens, total_tokens, cost) in enumerate(rows, 1):
        cost_str = f"${cost:.4f}" if cost > 0 else "N/A"
        print(
            f"{rank:<6} {display:<30} "
            f"{accuracy:>9.1f}% {latency:>11.0f}ms "
            f"{avg_tokens:>11.0f} {total_tokens:>13,} "
            f"{cost_str:>12}"
        )

    print("=" * 120)
    print()
