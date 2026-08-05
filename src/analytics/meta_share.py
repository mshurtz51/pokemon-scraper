"""
Tournament meta share report.
"""

import pandas as pd

from src.analytics_queries import (
    get_tournaments,
    get_classified_players,
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


def main():

    tournament_id, tournament_name = (
        select_tournament()
    )

    df = get_classified_players(
        tournament_id
    )

    total_players = len(df)

    #
    # Overall Meta Share
    #

    meta = (
        df.groupby("overall")
        .size()
        .reset_index(name="players")
    )

    meta["meta_share"] = (
        meta["players"]
        / total_players
        * 100
    )

    meta = meta.sort_values(
        "players",
        ascending=False,
    )

    print()
    print("=" * 60)
    print(tournament_name)
    print("=" * 60)
    print()

    print("Overall Meta Share")
    print("-" * 60)

    print(
        meta.to_string(
            index=False,
            formatters={
                "meta_share":
                    "{:.2f}%".format
            },
        )
    )

    #
    # Variant Breakdown
    #

    print()
    print("=" * 60)
    print("VARIANT BREAKDOWN")
    print("=" * 60)

    for overall in meta["overall"]:

        variants = df[
            df["overall"] == overall
        ]

        if len(variants) == 0:
            continue

        variant_table = (
            variants.groupby("variant")
            .size()
            .reset_index(name="players")
        )

        variant_table["meta_share"] = (
            variant_table["players"]
            / total_players
            * 100
        )

        variant_table["archetype_share"] = (
            variant_table["players"]
            / variant_table["players"].sum()
            * 100
        )

        variant_table = variant_table.sort_values(
            "players",
            ascending=False,
        )

        print()
        print(overall)
        print("-" * 60)

        print(
            variant_table.to_string(
                index=False,
                formatters={
                    "meta_share":
                        "{:.2f}%".format,
                    "archetype_share":
                        "{:.2f}%".format,
                },
            )
        )


if __name__ == "__main__":
    main()