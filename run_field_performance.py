"""Print archetype performance against the full tournament field."""

from __future__ import annotations

import argparse

from src.matchups import get_archetype_field_performance


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print archetype performance against the full field."
    )
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--division", default="Masters")
    parser.add_argument("--round", type=int, dest="max_round")
    parser.add_argument("--archetype")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--include-unknown", action="store_true")
    args = parser.parse_args()

    performance = get_archetype_field_performance(
        tournament_id=args.tournament_id,
        division=args.division,
        use_variants=args.variants,
        include_unknown=args.include_unknown,
        max_round=args.max_round,
    )
    if args.archetype:
        performance = performance[
            performance["archetype"] == args.archetype
        ]
    if performance.empty:
        print("No field-performance data matched those filters.")
        return

    performance = performance.copy()
    performance["win_rate"] = performance["win_rate"].map(
        lambda value: f"{value:.1%}" if value == value else "-"
    )
    print(performance.to_string(index=False))


if __name__ == "__main__":
    main()
