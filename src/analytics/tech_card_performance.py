"""
Tech card performance report.
"""

import pandas as pd

from src.analytics_queries import (
    get_tournaments,
    get_archetype_card_performance,
)


CUTS = [
    64,
    128,
    512,
]


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

def select_variant(df):

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
        input("\nSelect variant: ")
    )

    if choice == 1:

        return None

    return variants[
        choice - 2
    ]


def select_cut():

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

    return {
        1: 64,
        2: 128,
        3: 512,
    }[
        choice
    ]


def select_performance_type():

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


def select_minimum_inclusion():

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
        input("\nSelect: ")
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


def select_core_cards():

    print()
    print("=" * 60)
    print("100% CORE CARDS")
    print("=" * 60)
    print("1. Include")
    print("2. Exclude")

    choice = int(
        input("\nSelect: ")
    )

    return choice == 1


def performance_index(
    players,
    tournament_players,
    top_cut,
    denominator,
):

    if players == 0:

        return 0.0

    expected = (
        players
        / tournament_players
    ) * denominator

    if expected == 0:

        return 0.0

    return (
        top_cut
        / expected
    )


def summarize(
    df,
    tournament_players,
    cut,
    cumulative,
):
    """
    Return the Performance Index for a group of decks.
    """

    players = len(
        df
    )

    if cumulative:

        top_cut = len(
            df[
                df[
                    "standing"
                ] <= cut
            ]
        )

        denominator = cut

    else:

        previous = {
            64: 32,
            128: 64,
            512: 256,
        }[
            cut
        ]

        top_cut = len(
            df[
                (
                    df[
                        "standing"
                    ] > previous
                )
                &
                (
                    df[
                        "standing"
                    ] <= cut
                )
            ]
        )

        denominator = (
            cut
            - previous
        )

    return performance_index(
        players,
        tournament_players,
        top_cut,
        denominator,
    )

def main():

    (
        tournament_id,
        tournament_name,
    ) = select_tournament()

    df = (
        get_archetype_card_performance(
            tournament_id
        )
    )

    archetype = (
        select_archetype(
            df
        )
    )
    
    variant = (
    select_variant(
        df[
            df["overall"]
            == archetype
        ]
    )
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

    cut = (
        select_cut()
    )

    cumulative = (
        select_performance_type()
    )

    minimum_inclusion = (
        select_minimum_inclusion()
    )

    include_core = (
        select_core_cards()
    )

    tournament_players = (
        df["player_key"]
        .nunique()
    )

    rows = []

    cards = sorted(
        df["card_name"]
        .dropna()
        .unique()
    )

    for card in cards:

        with_players = (
            df[
                df[
                    "card_name"
                ] == card
            ]["player_key"]
            .unique()
        )

        with_df = (
            df[
                df[
                    "player_key"
                ].isin(
                    with_players
                )
            ]
            .drop_duplicates(
                "player_key"
            )
        )

        without_df = (
            df[
                ~df[
                    "player_key"
                ].isin(
                    with_players
                )
            ]
            .drop_duplicates(
                "player_key"
            )
        )

        with_pi = summarize(
            with_df,
            tournament_players,
            cut,
            cumulative,
        )

        without_pi = summarize(
            without_df,
            tournament_players,
            cut,
            cumulative,
        )

        rows.append(
            {
                "Card":
                    card,

                "Decks":
                    len(
                        with_df
                    ),

                "Others":
                    len(
                        without_df
                    ),

                "Inclusion":
                    (
                        len(
                            with_df
                        )
                        / tournament_players
                        * 100
                    ),

                "With PI":
                    with_pi,

                "Others PI":
                    without_pi,

                "Diff":
                    with_pi
                    - without_pi,
            }
        )

    report = pd.DataFrame(
        rows
    )

    report = report[
        report[
            "Inclusion"
        ]
        >= minimum_inclusion
    ]

    if not include_core:

        report = report[
            report[
                "Inclusion"
            ]
            < 100
        ]

    report = report.sort_values(
        "Diff",
        ascending=False,
    )

    print()
    print("=" * 60)
    print(
        tournament_name
    )
    print(
    archetype
)

if variant is None:

    print(
        "Overall"
    )

else:

    print(
        variant
    )
    print("TECH CARD PERFORMANCE")
    print(
        (
            "CUMULATIVE"
            if cumulative
            else "ACTUAL"
        )
        + f" TOP {cut}"
    )
    print("=" * 60)
    print()

    print(
        report.to_string(
            index=False,
            formatters={
                "Inclusion":
                    "{:.1f}%".format,

                "With PI":
                    "{:.2f}x".format,

                "Others PI":
                    "{:.2f}x".format,

                "Diff":
                    "{:+.2f}".format,
            },
        )
    )
        
if __name__ == "__main__":
    main()