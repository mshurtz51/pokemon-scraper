"""
Tournament top cut conversion report.
"""

from src.analytics_queries import (
    get_tournaments,
    get_tournament_results,
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

    df = get_tournament_results(
        tournament_id
    )

    total_players = len(df)

    cuts = [
        8,
        16,
        32,
        64,
        128,
        256,
        512,
    ]

    print()
    print("=" * 60)
    print(tournament_name)
    print("=" * 60)

    for cut in cuts:

        summary = (
            df.groupby("overall")
            .size()
            .reset_index(name="Players")
        )

        summary["Meta"] = (
            summary["Players"]
            / total_players
            * 100
        )

        top = (
            df[df["standing"] <= cut]
            .groupby("overall")
            .size()
            .reset_index(name=f"Top {cut}")
        )

        summary = summary.merge(
            top,
            on="overall",
            how="left",
        )

        summary = summary.fillna(0)

        summary[f"Top {cut}"] = (
            summary[f"Top {cut}"]
            .astype(int)
        )

        #
        # Only archetypes with at least one finish
        #

        summary = summary[
            summary[f"Top {cut}"] > 0
        ]

        #
        # Conversion
        #

        field_share = (
            summary["Players"]
            / total_players
        )

        top_share = (
            summary[f"Top {cut}"]
            / cut
        )

        summary["Conv"] = (
            top_share
            / field_share
        )

        summary = summary.sort_values(
            "Conv",
            ascending=False,
        )

        summary = summary.rename(
            columns={
                "overall": "Archetype",
            }
        )

        summary = summary[
            [
                "Archetype",
                "Players",
                "Meta",
                f"Top {cut}",
                "Conv",
            ]
        ]

        print()
        print("=" * 60)
        print(f"TOP {cut} CONVERSION")
        print("=" * 60)

        print(
            summary.to_string(
                index=False,
                formatters={
                    "Meta": "{:.1f}%".format,
                    "Conv": "{:.2f}x".format,
                },
            )
        )


if __name__ == "__main__":
    main()