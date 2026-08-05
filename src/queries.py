"""
Database query functions.
"""

import sqlite3

from src.config import DATABASE_NAME
from src.models import DeckCard


def get_connection():
    """
    Return a database connection.
    """

    return sqlite3.connect(str(DATABASE_NAME))


def get_players():
    """
    Return all players.
    """

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            player_key,
            tournament_id,
            first_name,
            last_name,
            standing
        FROM players
        ORDER BY tournament_id, standing
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_deck(player_key):
    """
    Return all cards for one deck.
    """

    conn = get_connection()

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