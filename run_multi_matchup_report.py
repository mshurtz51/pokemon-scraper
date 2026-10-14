"""Print aggregated matchup analytics across tournaments."""

from __future__ import annotations

import argparse

from src.matchups import get_multi_tournament_matchup_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print directed matchup results aggregated across tournaments."
    )
    parser.add_argument(
        "--tournament-id",
        action="append",
        dest="tournament_ids",
        help="Limit the report; repeat this option for multiple tournaments.",
    )
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--archetype")
    parser.add_argument("--opponent")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--include-unknown", action="store_true")
    args = parser.parse_args()

    report = get_multi_tournament_matchup_summary(
        tournament_ids=args.tournament_ids,
        archetype=args.archetype,
        opponent=args.opponent,
        division=args.division,
        use_variants=args.variants,
        include_unknown=args.include_unknown,
    )
    if report.empty:
        print("No multi-tournament matchup data matched those filters.")
        return

    report = report.copy()
    report["win_rate"] = report["win_rate"].map(
        lambda value: f"{value:.1%}" if value == value else "-"
    )
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
