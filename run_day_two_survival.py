"""Print the Day 2 survival/conversion curve by round."""

from __future__ import annotations

import argparse

from src.matchups import get_day_two_survival_curve


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print Day 2 survival and conversion by round."
    )
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--archetype")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--max-round", type=int)
    parser.add_argument(
        "--round",
        type=int,
        dest="selected_round",
        help="Show only one round, ordered by survivability index.",
    )
    args = parser.parse_args()

    report = get_day_two_survival_curve(
        tournament_id=args.tournament_id,
        division=args.division,
        use_variants=args.variants,
        max_round=args.max_round,
    )
    if args.archetype:
        report = report[report["group"] == args.archetype]
    if args.selected_round is not None:
        report = report[report["round"] == args.selected_round].copy()
        report = report.sort_values(
            ["survival_index", "group"],
            ascending=[False, True],
        )
    if report.empty:
        print("No Day 2 survival data matched those filters.")
        return

    for column in (
        "conversion_rate",
        "field_conversion_rate",
        "meta_share",
    ):
        report[column] = report[column].map(
            lambda value: f"{value:.2f}%" if value == value else "-"
        )
    report["survival_index"] = report["survival_index"].map(
        lambda value: f"{value:.2f}x" if value == value else "-"
    )
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
