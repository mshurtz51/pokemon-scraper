"""
QA tool for the deck archetype classifier.
"""

import sqlite3

from src.classifier import classify_deck
from src.config import DATABASE_NAME
from src.models import DeckCard


def random_player():
    """
    Return one random player from the database.
    """

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            player_key,
            first_name,
            last_name
        FROM players
        ORDER BY RANDOM()
        LIMIT 1
    """)

    player = cursor.fetchone()

    conn.close()

    return player


def load_deck(player_key):
    """
    Load one deck.
    """

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            quantity,
            card_name,
            card_type,
            set_code,
            card_number
        FROM deck_cards
        WHERE player_key = ?
    """, (player_key,))

    rows = cursor.fetchall()

    conn.close()

    cards = []

    for row in rows:

        cards.append(
            DeckCard(
                player_key=player_key,
                quantity=row[0],
                card_name=row[1],
                card_type=row[2],
                set_code=row[3],
                card_number=row[4],
            )
        )

    return cards


def main():

    player_key, first_name, last_name = random_player()

    cards = load_deck(player_key)

    result = classify_deck(cards)

    print("=" * 60)
    print(f"{first_name} {last_name}")
    print("=" * 60)
    print()

    print(f"Overall : {result.overall}")
    print(f"Variant : {result.variant}")
    print(f"Matched : {result.matched}")
    print(f"Score   : {result.score:.0%}")

    print()
    print("Rule Evaluation")
    print("-" * 60)

    for rule in result.rule_results:

        symbol = "✓" if rule.passed else "✗"

        print(
            f"{symbol} {rule.card_name} "
            f"{rule.operator} {rule.expected} "
            f"(Found: {rule.actual})"
        )

    print()
    print("Core Pokemon (2+ copies)")
    print("-" * 60)

    pokemon = sorted(
        [
            card
            for card in cards
            if card.card_type == "Pokemon" and card.quantity >= 2
        ],
        key=lambda x: (-x.quantity, x.card_name)
    )

    for card in pokemon:

        print(f"{card.quantity}x {card.card_name}")


if __name__ == "__main__":
    main()