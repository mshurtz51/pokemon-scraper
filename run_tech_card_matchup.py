"""Print matchup results for an archetype and selected tech card."""

from __future__ import annotations

import argparse

from src.matchups import get_tech_card_matchup_analysis


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze matchups for decks containing one selected card."
    )
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--card", required=True)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--opponent")
    parser.add_argument("--variants", action="store_true")
    args = parser.parse_args()

    report = get_tech_card_matchup_analysis(
        tournament_id=args.tournament_id,
        archetype=args.archetype,
        card_name=args.card,
        division=args.division,
        use_variants=args.variants,
    )
    if args.opponent:
        report = report[report["opponent"] == args.opponent]
    if report.empty:
        print("No tech-card matchup data matched those filters.")
        return

    for column in ("win_rate", "tie_rate", "decisive_win_rate"):
        report[column] = report[column].map(
            lambda value: f"{value:.1%}" if value == value else "-"
        )
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
