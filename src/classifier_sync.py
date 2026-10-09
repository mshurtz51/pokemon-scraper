"""
Synchronize deck classifications with the database.
"""

from collections import defaultdict

from src.classifier import classify_deck, prepare_rules
from src.database import get_connection
from src.metadata import load_archetypes
from src.models import DeckCard
from src.queries import (
    get_players,
)


def sync_classifications():
    """
    Classify every deck and update the players table.
    """

    players = get_players()

    total = len(players)

    print()
    print("=" * 60)
    print("SYNC CLASSIFICATIONS")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()
    cards_by_player = defaultdict(list)
    rows = cursor.execute(
        """
        SELECT player_key, quantity, card_name, card_type, set_code, card_number
        FROM deck_cards
        """
    ).fetchall()
    for row in rows:
        cards_by_player[row[0]].append(
            DeckCard(
                player_key=row[0],
                quantity=row[1],
                card_name=row[2],
                card_type=row[3],
                set_code=row[4],
                card_number=row[5],
            )
        )

    rules = prepare_rules(load_archetypes())

    for i, player in enumerate(players, start=1):

        player_key = player[0]

        print(f"{i}/{total}")

        result = classify_deck(cards_by_player[player_key], rules=rules)

        cursor.execute(
            """
            UPDATE players
            SET
                overall = ?,
                variant = ?,
                matched = ?,
                score = ?
            WHERE player_key = ?
            """,
            (
                result.overall,
                result.variant,
                int(result.matched),
                result.score,
                player_key,
            ),
        )

    conn.commit()

    conn.close()

    print()
    print("=" * 60)
    print("CLASSIFICATIONS SYNCHRONIZED")
    print("=" * 60)
