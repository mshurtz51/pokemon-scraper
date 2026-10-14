"""Print archetype performance by tournament round."""

from __future__ import annotations

import argparse

from src.matchups import get_archetype_round_performance


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print archetype win rates by round."
    )
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--round", type=int, dest="max_round")
    parser.add_argument("--archetype")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--include-unknown", action="store_true")
    parser.add_argument(
        "--day-2-filter",
        choices=("all", "yes", "no"),
        default="all",
    )
    args = parser.parse_args()

    contention = {"all": None, "yes": True, "no": False}[args.day_2_filter]
    report = get_archetype_round_performance(
        tournament_id=args.tournament_id,
        division=args.division,
        use_variants=args.variants,
        include_unknown=args.include_unknown,
        day_2_contention=contention,
        max_round=args.max_round,
    )
    if args.archetype:
        report = report[report["archetype"] == args.archetype]
    if report.empty:
        print("No round-performance data matched those filters.")
        return

    report = report.copy()
    report["win_rate"] = report["win_rate"].map(
        lambda value: f"{value:.1%}" if value == value else "-"
    )
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
