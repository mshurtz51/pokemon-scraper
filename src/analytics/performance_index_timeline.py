"""
Performance Index timeline by tournament.
"""

import pandas as pd

from src.analytics_queries import (
    get_tournaments,
    get_all_tournament_results,
)


def select_tournaments():
    """
    Let the user choose one or more tournaments.
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

    choices = input(
        "\nSelect tournaments (comma separated): "
    )

    indices = [
        int(x.strip()) - 1
        for x in choices.split(",")
    ]

    selected = tournaments.iloc[
        indices
    ]

    return selected


def select_cut():
    """
    Select Performance Index cut.
    """

    print()
    print("=" * 60)
    print("PERFORMANCE INDEX")
    print("=" * 60)
    print("1. Top 64")
    print("2. Top 128")
    print("3. Top 512")

    choice = int(
        input("\nSelect: ")
    )

    mapping = {
        1: 64,
        2: 128,
        3: 512,
    }

    return mapping[
        choice
    ]


def select_performance_type():
    """
    Select actual or cumulative Performance Index.
    """

    print()
    print("=" * 60)
    print("PERFORMANCE INDEX TYPE")
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

    tournaments = (
        select_tournaments()
    )

    cut = select_cut()

    cumulative = (
        select_performance_type()
    )

    results = (
        get_all_tournament_results()
    )

    report = None

    last_column = None

    for _, tournament in tournaments.iterrows():

        tournament_df = results[
            results["tournament_id"]
            == tournament[
                "tournament_id"
            ]
        ]

        total_players = len(
            tournament_df
        )

        rows = []

        for archetype in sorted(
            tournament_df[
                "overall"
            ].unique()
        ):

            deck_df = tournament_df[
                tournament_df[
                    "overall"
                ]
                == archetype
            ]

            players = len(
                deck_df
            )

            if cumulative:

                top_cut = len(
                    deck_df[
                        deck_df[
                            "standing"
                        ] <= cut
                    ]
                )

                denominator = cut

            else:

                previous_cut = {
                    64: 32,
                    128: 64,
                    512: 256,
                }[cut]

                top_cut = len(
                    deck_df[
                        (
                            deck_df[
                                "standing"
                            ] > previous_cut
                        )
                        &
                        (
                            deck_df[
                                "standing"
                            ] <= cut
                        )
                    ]
                )

                denominator = (
                    cut
                    - previous_cut
                )

            pi = performance_index(
                players,
                total_players,
                top_cut,
                denominator,
            )

            rows.append(
                {
                    "Archetype":
                        archetype,
                    tournament[
                        "tournament_name"
                    ]: pi,
                }
            )

        df = pd.DataFrame(
            rows
        )

        if report is None:

            report = df

        else:

            report = report.merge(
                df,
                on="Archetype",
                how="outer",
            )

        last_column = (
            tournament[
                "tournament_name"
            ]
        )

    report = report.fillna(
        0
    )

    #
    # Remove archetypes that are 0.00x
    # across every selected tournament.
    #

    tournament_columns = [
        column
        for column in report.columns
        if column != "Archetype"
    ]

    report = report[
        (
            report[
                tournament_columns
            ] > 0
        ).any(axis=1)
    ]

    report = report.sort_values(
        last_column,
        ascending=False,
    )

    print()
    print("=" * 60)
    print(
        f"PERFORMANCE INDEX TIMELINE (TOP {cut})"
    )
    print("=" * 60)
    print()

    formatters = {}

    for column in report.columns:

        if column != "Archetype":

            formatters[
                column
            ] = (
                "{:.2f}x".format
            )

    print(
        report.to_string(
            index=False,
            formatters=formatters,
        )
    )


if __name__ == "__main__":
    main()