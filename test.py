"""
QA test for scraping an entire tournament into SQLite.
"""

import time
import sqlite3

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
    print("FULL TOURNAMENT SCRAPE")
    print("=" * 60)

    start = time.time()

    # Create database
    create_database()

    # Parse roster
    print("\nParsing roster...")
    players, decks = parse_roster(TOURNAMENT_ID)

    print(f"Players found: {len(players)}")
    print(f"Decks found:   {len(decks)}")

    # Parse every deck
    print("\nDownloading and parsing every deck...")
    cards = parse_all_decks(players, decks)

    # Load database
    print("\nLoading SQLite database...")

    insert_players(players)
    insert_decks(decks)
    insert_cards(cards)

    # Verify
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

    print("\n" + "=" * 60)
    print("SCRAPE COMPLETE")
    print("=" * 60)

    print(f"Players      : {player_count}")
    print(f"Decks        : {deck_count}")
    print(f"Unique Cards : {card_count}")
    print(f"Elapsed Time : {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()