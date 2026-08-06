"""
Tournament metagame breakdown report.
"""

from src.analytics_queries import (
    get_tournaments,
    get_archetype_summary,
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


def main():

    tournament_id, tournament_name = (
        select_tournament()
    )

    df = get_archetype_summary(
        tournament_id
    )

    archetype = select_archetype(
        df
    )

    df = df[
        df["overall"] == archetype
    ]

    total_players = len(df)

    print()
    print("=" * 60)
    print(tournament_name)
    print(archetype)
    print("=" * 60)
    print()

    print("Overall")
    print("-" * 60)
    print(
        f"Players:      {total_players}"
    )
    print()

    variant_summary = (
        df.groupby("variant")
        .agg(
            Players=(
                "player_key",
                "count",
            ),
            Average_Finish=(
                "standing",
                "mean",
            ),
            Median_Finish=(
                "standing",
                "median",
            ),
            Best_Finish=(
                "standing",
                "min",
            ),
        )
        .reset_index()
    )

    variant_summary["Share"] = (
        variant_summary["Players"]
        / total_players
        * 100
    )

    variant_summary = variant_summary.sort_values(
        "Players",
        ascending=False,
    )

    print("=" * 60)
    print("VARIANT META SHARE")
    print("=" * 60)
    print()

    print(
        variant_summary[
            [
                "variant",
                "Players",
                "Share",
            ]
        ].to_string(
            index=False,
            formatters={
                "Share":
                    "{:.1f}%".format,
            },
        )
    )

    print()
    print("=" * 60)
    print("VARIANT PERFORMANCE")
    print("=" * 60)
    print()

    print(
        variant_summary[
            [
                "variant",
                "Average_Finish",
                "Median_Finish",
                "Best_Finish",
            ]
        ].to_string(
            index=False,
            formatters={
                "Average_Finish":
                    "{:.1f}".format,
                "Median_Finish":
                    "{:.1f}".format,
            },
        )
    )


if __name__ == "__main__":
    main()