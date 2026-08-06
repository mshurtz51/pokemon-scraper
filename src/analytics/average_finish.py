"""
Tournament average finish report.
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

    summary = (
        df.groupby("overall")
        .agg(
            Players=("overall", "size"),
            Average_Finish=("standing", "mean"),
            Median_Finish=("standing", "median"),
            Best_Finish=("standing", "min"),
            Worst_Finish=("standing", "max"),
        )
        .reset_index()
    )

    summary = summary.rename(
        columns={
            "overall": "Archetype",
        }
    )

    summary = summary.sort_values(
        "Average_Finish"
    )

    print()
    print("=" * 60)
    print(tournament_name)
    print("=" * 60)
    print()

    print(
        summary.to_string(
            index=False,
            formatters={
                "Average_Finish": "{:.1f}".format,
                "Median_Finish": "{:.1f}".format,
            },
        )
    )


if __name__ == "__main__":
    main()