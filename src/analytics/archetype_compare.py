"""
Compare multiple archetypes side-by-side.
"""

import pandas as pd

from src.analytics_queries import (
    get_tournaments,
    get_archetype_summary,
)


CUTS = [
    8,
    16,
    32,
    64,
    128,
    256,
    512,
]


def select_tournament():
    """
    Let the user choose a tournament.
    """

    tournaments = get_tournaments()

    print()
    print("=" * 60)
    print("TOURNAMENTS")
    print("=" * 60)

    for i, row in tournaments.iterrows():

        print(
            f"{i + 1}. "
            f"{row['tournament_name']}"
        )

    choice = int(
        input("\nSelect tournament: ")
    )

    tournament = tournaments.iloc[
        choice - 1
    ]

    return (
        tournament["tournament_id"],
        tournament["tournament_name"],
    )


def select_archetypes(df):
    """
    Let the user choose 2-5 archetypes.
    """

    archetypes = sorted(
        df["overall"].unique()
    )

    print()
    print("=" * 60)
    print("ARCHETYPES")
    print("=" * 60)

    for i, archetype in enumerate(
        archetypes,
        start=1,
    ):

        print(
            f"{i}. {archetype}"
        )

    number = int(
        input(
            "\nHow many archetypes (2-5)? "
        )
    )

    selected = []

    for i in range(number):

        choice = int(
            input(
                f"Select archetype #{i + 1}: "
            )
        )

        selected.append(
            archetypes[
                choice - 1
            ]
        )

    return selected


def select_performance_type():
    """
    Select actual or cumulative Performance Index.
    """

    print()
    print("=" * 60)
    print("PERFORMANCE INDEX")
    print("=" * 60)
    print("1. Actual")
    print("2. Cumulative")

    choice = int(
        input("\nSelect: ")
    )

    return choice == 2


def performance_index(
    archetype_players,
    total_players,
    top_cut_players,
    cut_size,
):
    """
    Calculate Performance Index.
    """

    if archetype_players == 0:
        return 0.0

    expected = (
        archetype_players
        / total_players
    ) * cut_size

    if expected == 0:
        return 0.0

    return (
        top_cut_players
        / expected
    )


def main():

    tournament_id, tournament_name = (
        select_tournament()
    )

    df = get_archetype_summary(
        tournament_id
    )

    archetypes = select_archetypes(
        df
    )

    cumulative = (
        select_performance_type()
    )

    total_players = len(df)

    metrics = []

    for archetype in archetypes:

        deck_df = df[
            df["overall"] == archetype
        ]

        row = {
            "Archetype": archetype,
            "Players": len(deck_df),
            "Meta Share":
                len(deck_df)
                / total_players
                * 100,
            "Average Finish":
                deck_df["standing"].mean(),
        }

        previous_cut = 0

        pi_values = {}

        for cut in CUTS:

            if cumulative:

                count = len(
                    deck_df[
                        deck_df["standing"] <= cut
                    ]
                )

                denominator = cut

            else:

                count = len(
                    deck_df[
                        (
                            deck_df["standing"]
                            > previous_cut
                        )
                        &
                        (
                            deck_df["standing"]
                            <= cut
                        )
                    ]
                )

                denominator = (
                    cut
                    - previous_cut
                )

            pi_values[cut] = performance_index(
                len(deck_df),
                total_players,
                count,
                denominator,
            )

            previous_cut = cut

        row["PI Top 64"] = pi_values[64]
        row["PI Top 128"] = pi_values[128]
        row["PI Top 512"] = pi_values[512]

        metrics.append(row)

    report = pd.DataFrame(metrics)

    report = report.sort_values(
        "PI Top 64",
        ascending=False,
    )

    print()
    print("=" * 60)
    print(tournament_name)
    print("ARCHETYPE COMPARISON")
    print("=" * 60)
    print()

    print(
        report.to_string(
            index=False,
            formatters={
                "Players":
                    "{:.0f}".format,
                "Meta Share":
                    "{:.1f}%".format,
                "Average Finish":
                    "{:.0f}".format,
                "PI Top 64":
                    "{:.2f}x".format,
                "PI Top 128":
                    "{:.2f}x".format,
                "PI Top 512":
                    "{:.2f}x".format,
            },
        )
    )


if __name__ == "__main__":
    main()