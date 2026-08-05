"""
Synchronize deck classifications with the database.
"""

from src.classifier import classify_deck
from src.database import get_connection
from src.queries import (
    get_players,
    get_deck,
)


def sync_classifications():
    """
    Classify every deck and update the players table.
    """

    conn = get_connection()

    cursor = conn.cursor()

    players = get_players()

    total = len(players)

    print()
    print("=" * 60)
    print("SYNC CLASSIFICATIONS")
    print("=" * 60)

    for i, player in enumerate(players, start=1):

        player_key = player[0]

        print(f"{i}/{total}")

        cards = get_deck(player_key)

        result = classify_deck(cards)

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