"""Print matchup analytics from the local SQLite databases."""

from __future__ import annotations

import argparse

from src.matchups import (
    flatten_matchup_round_cohorts,
    get_matchup_round_cohorts,
    get_matchup_round_matrix,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print round-by-round and total archetype matchup rates."
    )
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument(
        "--round",
        type=int,
        dest="max_round",
        help="Only include matches through this round.",
    )
    parser.add_argument("--archetype")
    parser.add_argument("--opponent")
    parser.add_argument(
        "--day-2-filter",
        choices=("all", "yes", "no"),
        default="all",
        help="Restrict results to opponents who can or cannot reach Day 2.",
    )
    parser.add_argument(
        "--show-day-2-field",
        choices=("yes", "no"),
        default="yes",
        help="Include the Day 2 contention column in long output.",
    )
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--include-unknown", action="store_true")
    args = parser.parse_args()

    contention = {
        "all": None,
        "yes": True,
        "no": False,
    }[args.day_2_filter]
    cohorts = get_matchup_round_cohorts(
        max_round=args.max_round,
        cumulative=False,
        tournament_id=args.tournament_id,
        min_games=1,
        use_variants=args.variants,
        include_unknown=args.include_unknown,
        day_2_contention=contention,
    )
    if args.archetype or args.opponent:
        if args.archetype:
            cohorts = cohorts[cohorts["archetype"] == args.archetype]
        if args.opponent:
            cohorts = cohorts[cohorts["opponent"] == args.opponent]
        if cohorts.empty:
            print("No matchup data matched those filters.")
            return
        display_cohorts = cohorts.copy()
        display_cohorts["win_rate"] = display_cohorts["win_rate"].map(
            lambda value: f"{value:.1%}" if value == value else "-"
        )
        columns = [
            "round",
            "matchup",
            "games",
            "wins",
            "losses",
            "ties_or_unknown",
            "win_rate",
        ]
        if args.show_day_2_field == "yes":
            columns.insert(2, "day_2_contention")
        print(display_cohorts[columns].to_string(index=False))
        totals = flatten_matchup_round_cohorts(cohorts)
        totals["win_rate"] = totals["win_rate"].map(
            lambda value: f"{value:.1%}" if value == value else "-"
        )
        if args.show_day_2_field == "no":
            columns.remove("day_2_contention") if "day_2_contention" in columns else None
        print("\nTOTAL")
        print(totals[columns].to_string(index=False))
        return

    matrix = get_matchup_round_matrix(
        max_round=args.max_round,
        cumulative=False,
        tournament_id=args.tournament_id,
        min_games=1,
        use_variants=args.variants,
        include_unknown=args.include_unknown,
        day_2_contention=contention,
    )
    if matrix.empty:
        print("No matchup data matched those filters.")
        return

    print(
        matrix.fillna("-").to_string(
            float_format=lambda value: f"{value:.1%}"
        )
    )


if __name__ == "__main__":
    main()
