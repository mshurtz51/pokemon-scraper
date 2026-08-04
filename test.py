"""
QA test for inserting players into SQLite.
"""

import sqlite3

from src.database import create_database, insert_players
from src.roster import parse_roster
from src.config import DATABASE_NAME

TOURNAMENT_ID = "TU01w1D52rjGebrE8szS"


def main():

    # Create database
    create_database()

    # Parse players
    players, decks = parse_roster(TOURNAMENT_ID)

    # Insert players
    insert_players(players)

    # Verify count
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM players")

    count = cursor.fetchone()[0]

    conn.close()

    print(f"Players parsed   : {len(players)}")
    print(f"Players in table : {count}")


if __name__ == "__main__":
    main()