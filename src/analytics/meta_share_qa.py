# -*- coding: utf-8 -*-

"""
QA report for validating archetype classifications.
"""

import pandas as pd

from src.analytics_queries import (
    get_tournaments,
    get_classified_players,
    get_deck,
)
from src.classifier import classify_deck
from src.config import EXPORT_FOLDER


def select_tournament():
    """
    Prompt the user to select a tournament.
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

    choice = int(input("\nSelect tournament: "))

    tournament = tournaments.iloc[
        choice - 1
    ]

    return (
        tournament["tournament_id"],
        tournament["tournament_name"],
    )


def core_cards(deck, card_type, minimum=2):
    """
    Return core cards.
    """

    cards = deck[
        (deck["card_type"] == card_type)
        & (deck["quantity"] >= minimum)
    ]

    cards = cards.sort_values(
        ["quantity", "card_name"],
        ascending=[False, True],
    )

    return ", ".join(
        f"{row.quantity}x {row.card_name}"
        for row in cards.itertuples()
    )


def failed_rules(rule_results):
    """
    Return failed rules.
    """

    failed = []

    for rule in rule_results:

        if not rule.passed:

            failed.append(
                f"{rule.card_name} {rule.operator} "
                f"{rule.expected} (Found {rule.actual})"
            )

    return " | ".join(failed)


def main():

    tournament_id, tournament_name = (
        select_tournament()
    )

    overall_filter = input(
        "Overall archetype (blank = all): "
    ).strip()

    matched_filter = input(
        "Matched (Y/N/blank): "
    ).strip().upper()

    players = get_classified_players(
        tournament_id
    )

    report = []

    total = len(players)

    for i, player in enumerate(
        players.itertuples(),
        start=1,
    ):

        print(f"{i}/{total}")

        deck_df = get_deck(
            player.player_key
        )

        # Rebuild DeckCard objects for classifier
        from src.models import DeckCard

        cards = []

        for row in deck_df.itertuples():

            cards.append(
                DeckCard(
                    player_key=player.player_key,
                    quantity=row.quantity,
                    card_name=row.card_name,
                    card_type=row.card_type,
                    set_code="",
                    card_number="",
                )
            )

        result = classify_deck(cards)

        if (
            overall_filter
            and result.overall != overall_filter
        ):
            continue

        if (
            matched_filter == "Y"
            and not result.matched
        ):
            continue

        if (
            matched_filter == "N"
            and result.matched
        ):
            continue

        report.append({

            "standing": player.standing,

            "player":
                f"{player.first_name} {player.last_name}",

            "overall": result.overall,

            "variant": result.variant,

            "matched": result.matched,

            "score": result.score,

            "failed_rules":
                failed_rules(result.rule_results),

            "core_pokemon":
                core_cards(
                    deck_df,
                    "pokemon",
                ),

            "core_trainers":
                core_cards(
                    deck_df,
                    "trainer",
                ),

        })

    df = pd.DataFrame(report)

    df = df.sort_values(
        ["overall", "standing"]
    )

    output = (
        EXPORT_FOLDER
        / "meta_share_qa.xlsx"
    )

    df.to_excel(
        output,
        index=False,
    )

    print()
    print(f"Saved report to:\n{output}")


if __name__ == "__main__":
    main()