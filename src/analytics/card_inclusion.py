"""
Card inclusion report.
"""

from src.analytics_queries import (
    get_tournaments,
    get_archetype_cards,
)


def select_tournament():

    tournaments = get_tournaments()

    print()
    print("=" * 60)
    print("TOURNAMENTS")
    print("=" * 60)

    for i, row in tournaments.iterrows():

        print(
            f"{i + 1}. {row['tournament_name']}"
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


def print_report(df, title):
    """
    Print card inclusion report for one group of decks.
    """

    total_decks = (
        df["player_key"]
        .nunique()
    )

    summary = (
        df.groupby(
            [
                "card_name",
                "card_type",
            ]
        )
        .agg(
            Decks=(
                "player_key",
                "nunique",
            ),
            Average_Copies=(
                "quantity",
                "mean",
            ),
        )
        .reset_index()
    )

    summary["Inclusion"] = (
        summary["Decks"]
        / total_decks
        * 100
    )

    summary = summary.sort_values(
        [
            "Inclusion",
            "Average_Copies",
            "card_name",
        ],
        ascending=[
            False,
            False,
            True,
        ],
    )

    print()
    print("=" * 60)
    print(
        f"{title} ({total_decks} Decks)"
    )
    print("=" * 60)
    print()

    print(
        summary.to_string(
            index=False,
            columns=[
                "card_name",
                "card_type",
                "Decks",
                "Inclusion",
                "Average_Copies",
            ],
            formatters={
                "Inclusion":
                    "{:.1f}%".format,
                "Average_Copies":
                    "{:.2f}".format,
            },
        )
    )

def main():

    tournament_id, tournament_name = (
        select_tournament()
    )

    df = get_archetype_cards(
        tournament_id
    )

    archetype = select_archetype(
        df
    )

    variant = select_variant(
        df[
            df["overall"]
            == archetype
        ]
    )

    df = df[
        df["overall"]
        == archetype
    ]

    if variant is not None:

        df = df[
            df["variant"]
            == variant
        ]

    print()
    print("=" * 60)
    print(tournament_name)
    print(archetype)

    if variant is None:

        print("Overall")

    else:

        print(variant)

    print("=" * 60)

    print_report(
        df,
        (
            "OVERALL"
            if variant is None
            else variant
        ),
    )


if __name__ == "__main__":
    main()