"""Print card-level performance inside one directed matchup."""

from __future__ import annotations

import argparse

from src.matchups import get_card_matchup_performance


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare cards inside one archetype matchup."
    )
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--card")
    args = parser.parse_args()

    report = get_card_matchup_performance(
        tournament_id=args.tournament_id,
        archetype=args.archetype,
        opponent=args.opponent,
        division=args.division,
        use_variants=args.variants,
    )
    if args.card:
        report = report[report["card_name"] == args.card]
    if report.empty:
        print("No card-level matchup data matched those filters.")
        return

    for column in (
        "win_rate_with_card",
        "win_rate_without_card",
        "win_rate_delta",
    ):
        report[column] = report[column].map(
            lambda value: f"{value:.1%}" if value == value else "-"
        )
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
