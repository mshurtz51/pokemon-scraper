"""
QA test for loading an entire tournament into SQLite.
"""

import os
import sqlite3
import sys
import time

# Allow imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import DATABASE_NAME
from src.database import (
    create_database,
    insert_players,
    insert_decks,
    insert_cards,
)
from src.roster import parse_roster
from src.scraper import parse_all_decks

TOURNAMENT_ID = "TU01w1D52rjGebrE8szS"


def main():

    print("=" * 60)
    print("FULL TOURNAMENT DATABASE QA")
    print("=" * 60)

    start = time.time()

    # Remove old database if it exists
    if os.path.exists(DATABASE_NAME):
        os.remove(DATABASE_NAME)

    create_database()

    players, decks = parse_roster(TOURNAMENT_ID)

    cards = parse_all_decks(players, decks)

    insert_players(players)
    insert_decks(decks)
    insert_cards(cards)

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM players")
    player_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decks")
    deck_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM deck_cards")
    card_count = cursor.fetchone()[0]

    conn.close()

    elapsed = time.time() - start

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"Players      : {player_count}")
    print(f"Decks        : {deck_count}")
    print(f"Deck Cards   : {card_count}")
    print(f"Elapsed Time : {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()