"""
Meta Share timeline by tournament.
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

    return tournaments.iloc[
        indices
    ]


def select_level():
    """
    Select archetype or variant.
    """

    print()
    print("=" * 60)
    print("LEVEL")
    print("=" * 60)
    print("1. Archetype")
    print("2. Variant")

    choice = int(
        input("\nSelect: ")
    )

    if choice == 1:

        return "overall"

    return "variant"


def select_archetype(df):
    """
    Let the user choose an archetype.
    """

    archetypes = sorted(
        df["overall"]
        .dropna()
        .unique()
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
        input(
            "\nSelect archetype: "
        )
    )

    return archetypes[
        choice - 1
    ]

def main():

    tournaments = (
        select_tournaments()
    )

    level = (
        select_level()
    )

    results = (
        get_all_tournament_results()
    )

    archetype = None

    if level == "variant":

        archetype = (
            select_archetype(
                results
            )
        )

        results = results[
            results["overall"]
            == archetype
        ]

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

        for group in sorted(
            tournament_df[
                level
            ]
            .dropna()
            .unique()
        ):

            deck_df = tournament_df[
                tournament_df[
                    level
                ]
                == group
            ]

            players = len(
                deck_df
            )

            meta_share = (
                players
                / total_players
                * 100
            )

            rows.append(
                {
                    "Group":
                        group,
                    tournament[
                        "tournament_name"
                    ]: meta_share,
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
                on="Group",
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

    tournament_columns = [
        column
        for column in report.columns
        if column != "Group"
    ]

    report = report[
        (
            report[
                tournament_columns
            ] > 0
        ).any(
            axis=1
        )
    ]

    report = report.sort_values(
        last_column,
        ascending=False,
    )

    print()
    print("=" * 60)

    if level == "overall":

        print(
            "ARCHETYPE META SHARE TIMELINE"
        )

    else:

        print(
            archetype
        )

        print(
            "VARIANT META SHARE TIMELINE"
        )

    print("=" * 60)
    print()

    formatters = {}

    for column in tournament_columns:

        formatters[
            column
        ] = (
            "{:.1f}%".format
        )

    print(
        report.to_string(
            index=False,
            formatters=formatters,
        )
    )
    
if __name__ == "__main__":
    main()