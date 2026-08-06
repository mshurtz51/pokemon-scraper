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

    df = df[
        df["overall"] == archetype
    ]

    print()
    print("=" * 60)
    print(tournament_name)
    print(archetype)
    print("=" * 60)

    #
    # Overall archetype
    #

    print_report(
        df,
        "OVERALL",
    )

    #
    # Variants (largest to smallest)
    #

    variants = (
        df.groupby("variant")["player_key"]
        .nunique()
        .sort_values(ascending=False)
    )

    for variant, _ in variants.items():

        variant_df = df[
            df["variant"] == variant
        ]

        print_report(
            variant_df,
            variant,
        )


if __name__ == "__main__":
    main()