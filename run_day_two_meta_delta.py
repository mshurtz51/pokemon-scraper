"""Compare Day 2 field composition between two tournament rounds."""

from __future__ import annotations

import argparse

from src.matchups import get_day_two_meta_share_delta


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Day 2 archetype or variant meta share by round."
    )
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--start-round", type=int, default=1)
    parser.add_argument("--end-round", type=int, default=8)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--variants", action="store_true")
    args = parser.parse_args()

    report = get_day_two_meta_share_delta(
        tournament_id=args.tournament_id,
        start_round=args.start_round,
        end_round=args.end_round,
        division=args.division,
        use_variants=args.variants,
    )
    if report.empty:
        print("No Day 2 field-composition data matched those filters.")
        return

    for column in (
        "start_meta_share",
        "end_meta_share",
        "delta_percentage_points",
    ):
        report[column] = report[column].map(lambda value: f"{value:+.2f}%")
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
