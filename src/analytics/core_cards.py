"""
Core card report.
"""

from src.analytics_queries import (
    get_tournaments,
    get_archetype_cards,
)


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


def print_bucket(summary, minimum, maximum, title):
    """
    Print one inclusion bucket.
    """

    bucket = summary[
        (summary["Inclusion"] >= minimum)
        & (summary["Inclusion"] < maximum)
    ]

    if bucket.empty:
        return

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    print(
        bucket[
            [
                "card_name",
                "Average_Copies",
                "Inclusion",
            ]
        ].to_string(
            index=False,
            formatters={
                "Average_Copies":
                    "{:.2f}".format,
                "Inclusion":
                    "{:.1f}%".format,
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
    print(tournament_name)
    print(archetype)
    print("=" * 60)

    print_bucket(
        summary,
        100,
        101,
        "100% CORE",
    )

    print_bucket(
        summary,
        95,
        100,
        "95-99% CORE",
    )

    print_bucket(
        summary,
        80,
        95,
        "80-94% COMMON",
    )

    print_bucket(
        summary,
        50,
        80,
        "50-79% FLEX",
    )

    print_bucket(
        summary,
        20,
        50,
        "20-49% TECH",
    )

    print_bucket(
        summary,
        0,
        20,
        "<20% RARE TECH",
    )


if __name__ == "__main__":
    main()