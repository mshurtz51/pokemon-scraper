"""Print field-weighted tech-card value analytics."""

from __future__ import annotations

import argparse

from src.matchups import get_tech_card_value_analysis


def format_percent(value: object) -> str:
    return f"{value:.1%}" if value == value else "-"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate a tech card's value above replacement."
    )
    parser.add_argument("--tournament-id")
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--card", required=True)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--variant")
    args = parser.parse_args()

    reports = get_tech_card_value_analysis(
        tournament_id=args.tournament_id,
        archetype=args.archetype,
        card_name=args.card,
        division=args.division,
        use_variants=args.variants,
        variant=args.variant,
    )
    summary = reports["summary"]
    if summary.empty:
        print("No tech-card value data matched those filters.")
        return

    for frame_name, frame in reports.items():
        frame = frame.copy()
        for column in frame.columns:
            if column == "match_point_delta_per_game":
                frame[column] = frame[column].map(
                    lambda value: f"{value:.3f}" if value == value else "-"
                )
                continue
            if column == "match_point_delta_per_100_games":
                frame[column] = frame[column].map(
                    lambda value: f"{value:.1f}" if value == value else "-"
                )
                continue
            if column == "tech_value_above_replacement":
                frame[column] = frame[column].map(format_percent)
                continue
            if "rate" in column or "delta" in column or "share" in column:
                frame[column] = frame[column].map(format_percent)
        print(f"\n{frame_name.upper()}")
        print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
