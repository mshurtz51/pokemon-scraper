"""
Card inclusion timeline report.
"""

import pandas as pd

from src.analytics_queries import (
    get_tournaments,
    get_all_archetype_cards,
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


def select_variant(df):
    """
    Let the user choose a variant.
    """

    variants = sorted(
        df["variant"]
        .dropna()
        .unique()
    )

    print()
    print("=" * 60)
    print("VARIANTS")
    print("=" * 60)
    print("1. Overall")

    for i, variant in enumerate(
        variants,
        start=2,
    ):

        print(
            f"{i}. {variant}"
        )

    choice = int(
        input(
            "\nSelect variant: "
        )
    )

    if choice == 1:

        return None

    return variants[
        choice - 2
    ]


def select_minimum_inclusion():
    """
    Let the user choose a minimum inclusion.
    """

    print()
    print("=" * 60)
    print("MINIMUM INCLUSION")
    print("=" * 60)
    print("1. 0%")
    print("2. 5%")
    print("3. 10%")
    print("4. 20%")
    print("5. Custom")

    choice = int(
        input(
            "\nSelect: "
        )
    )

    mapping = {
        1: 0,
        2: 5,
        3: 10,
        4: 20,
    }

    if choice == 5:

        return float(
            input(
                "\nMinimum Inclusion (%): "
            )
        )

    return mapping[
        choice
    ]
def main():

    tournaments = (
        select_tournaments()
    )

    df = (
        get_all_archetype_cards()
    )

    tournament_ids = (
        tournaments[
            "tournament_id"
        ]
        .tolist()
    )

    df = df[
        df[
            "tournament_id"
        ]
        .isin(
            tournament_ids
        )
    ]

    archetype = (
        select_archetype(
            df
        )
    )

    df = df[
        df["overall"]
        == archetype
    ]

    variant = (
        select_variant(
            df
        )
    )

    if variant is not None:

        df = df[
            df["variant"]
            == variant
        ]

    minimum_inclusion = (
        select_minimum_inclusion()
    )

    rows = []

    for _, tournament in tournaments.iterrows():

        tournament_df = (
            df[
                df[
                    "tournament_id"
                ]
                == tournament[
                    "tournament_id"
                ]
            ]
        )

        total_decks = (
            tournament_df[
                "player_key"
            ]
            .nunique()
        )

        summary = (
            tournament_df
            .groupby(
                "card_name"
            )
            .agg(
                Decks=(
                    "player_key",
                    "nunique",
                )
            )
            .reset_index()
        )

        summary[
            tournament[
                "tournament_name"
            ]
        ] = (
            summary[
                "Decks"
            ]
            / total_decks
            * 100
        )

        summary = summary[
            [
                "card_name",
                tournament[
                    "tournament_name"
                ],
            ]
        ]

        rows.append(
            summary
        )

    report = rows[0]

    for table in rows[1:]:

        report = report.merge(
            table,
            on="card_name",
            how="outer",
        )

    report = report.fillna(
        0
    )

    tournament_columns = [
        t
        for t in report.columns
        if t != "card_name"
    ]

    report = report[
        report[
            tournament_columns
        ]
        .max(axis=1)
        >= minimum_inclusion
    ]

    last_column = (
        tournaments.iloc[-1][
            "tournament_name"
        ]
    )

    report = report.sort_values(
        last_column,
        ascending=False,
    )

    print()
    print("=" * 60)
    print("CARD INCLUSION TIMELINE")
    print("=" * 60)
    print()

    print(
        report.to_string(
            index=False,
            formatters={
                column:
                    "{:.1f}%".format
                for column
                in tournament_columns
            },
        )
    )
        
if __name__ == "__main__":
    main()