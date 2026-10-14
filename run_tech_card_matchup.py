"""Print matchup results for an archetype and selected tech card."""

from __future__ import annotations

import argparse

import pandas as pd

from src.matchups import get_tech_card_matchup_analysis


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze matchups for decks containing one selected card."
    )
    parser.add_argument(
        "--tournament-id",
        help="Limit the report to one tournament; omit for all tournaments.",
    )
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--card", required=True)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--opponent")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument(
        "--variant",
        help="Select one exact focal variant together with --archetype.",
    )
    args = parser.parse_args()

    report = get_tech_card_matchup_analysis(
        tournament_id=args.tournament_id,
        archetype=args.archetype,
        card_name=args.card,
        division=args.division,
        use_variants=args.variants,
        variant=args.variant,
    )
    if args.opponent:
        report = report[report["opponent"] == args.opponent]
    if report.empty:
        print("No tech-card matchup data matched those filters.")
        return

    total = {
        "opponent": "TOTAL",
        "players_without_card": None,
        "players_with_card": None,
    }
    for presence in ("without_card", "with_card"):
        for metric in ("games", "wins", "losses", "ties", "decisive_games"):
            total[f"{metric}_{presence}"] = report[
                f"{metric}_{presence}"
            ].sum()
        games = total[f"games_{presence}"]
        decisive_games = total[f"decisive_games_{presence}"]
        total[f"win_rate_{presence}"] = (
            total[f"wins_{presence}"] + total[f"ties_{presence}"] / 3
        ) / games
        total[f"tie_rate_{presence}"] = total[f"ties_{presence}"] / games
        total[f"decisive_win_rate_{presence}"] = (
            total[f"wins_{presence}"] / decisive_games
            if decisive_games
            else float("nan")
        )
    total["win_rate_delta"] = (
        total["win_rate_with_card"] - total["win_rate_without_card"]
    )
    total["tie_rate_delta"] = (
        total["tie_rate_with_card"] - total["tie_rate_without_card"]
    )
    total["card_name"] = report.iloc[0]["card_name"]
    total["archetype"] = report.iloc[0]["archetype"]
    total["grouping"] = report.iloc[0]["grouping"]
    report = pd.concat([report, pd.DataFrame([total])], ignore_index=True)

    for column in (
        "win_rate_with_card",
        "win_rate_without_card",
        "tie_rate_with_card",
        "tie_rate_without_card",
        "decisive_win_rate_with_card",
        "decisive_win_rate_without_card",
        "win_rate_delta",
        "tie_rate_delta",
    ):
        report[column] = report[column].map(
            lambda value: f"{value:.1%}" if value == value else "-"
        )
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
