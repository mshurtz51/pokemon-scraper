"""
Compare variants within one archetype.
"""

import pandas as pd

from src.analytics_queries import (
    get_tournaments,
    get_archetype_summary,
)


CUTS = [
    64,
    128,
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


def select_archetype(df):
    """
    Let the user choose an archetype.
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

    choice = int(
        input("\nSelect archetype: ")
    )

    return archetypes[
        choice - 1
    ]


def select_performance_type():
    """
    Select actual or cumulative PI.
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

    (
        tournament_id,
        tournament_name,
    ) = select_tournament()

    df = get_archetype_summary(
        tournament_id
    )

    archetype = select_archetype(
        df
    )

    cumulative = (
        select_performance_type()
    )

    #
    # Tournament player count
    #

    tournament_players = len(
        df
    )

    #
    # Only selected archetype
    #

    df = df[
        df["overall"]
        == archetype
    ]

    archetype_players = len(
        df
    )

    rows = []

    for variant in sorted(
        df["variant"].unique()
    ):

        variant_df = df[
            df["variant"]
            == variant
        ]

        players = len(
            variant_df
        )

        row = {
            "Variant":
                variant,
            "Players":
                players,
            "Share":
                players
                / archetype_players
                * 100,
            "Average Finish":
                variant_df[
                    "standing"
                ].mean(),
            "Median Finish":
                variant_df[
                    "standing"
                ].median(),
            "Best Finish":
                int(
                    variant_df[
                        "standing"
                    ].min()
                ),
        }

        for cut in CUTS:

            if cumulative:

                count = len(
                    variant_df[
                        variant_df[
                            "standing"
                        ]
                        <= cut
                    ]
                )

                denominator = cut

            else:

                previous_cut = {
                    64: 32,
                    128: 64,
                    512: 256,
                }[
                    cut
                ]

                count = len(
                    variant_df[
                        (
                            variant_df[
                                "standing"
                            ]
                            > previous_cut
                        )
                        &
                        (
                            variant_df[
                                "standing"
                            ]
                            <= cut
                        )
                    ]
                )

                denominator = (
                    cut
                    - previous_cut
                )

            row[
                f"PI Top {cut}"
            ] = performance_index(
                players,
                tournament_players,
                count,
                denominator,
            )

        rows.append(
            row
        )

    report = pd.DataFrame(
        rows
    )

    report = report.sort_values(
        "PI Top 512",
        ascending=False,
    )

    print()
    print("=" * 60)
    print(
        tournament_name
    )
    print(
        archetype
    )
    print("VARIANT COMPARISON")
    print("=" * 60)
    print()

    print(
        report.to_string(
            index=False,
            formatters={
                "Share":
                    "{:.1f}%".format,
                "Average Finish":
                    "{:.0f}".format,
                "Median Finish":
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