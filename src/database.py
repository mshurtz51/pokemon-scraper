"""
SQLite database functions.
"""

import sqlite3

from src.config import DATABASE_NAME


def get_connection():
    """
    Return a connection to the SQLite database.
    """

    return sqlite3.connect(DATABASE_NAME)


def create_database():
    """
    Create the SQLite database and all tables.
    """

    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------
    # tournaments
    # -----------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tournaments (

        tournament_id TEXT PRIMARY KEY,

        name TEXT,

        date TEXT,

        city TEXT,

        country TEXT,

        season INTEGER,

        format TEXT

    )
    """)

    # -----------------------------
    # players
    # -----------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (

        player_key TEXT PRIMARY KEY,

        tournament_id TEXT,

        first_name TEXT,

        last_name TEXT,

        country TEXT,

        division TEXT,

        standing INTEGER

    )
    """)

    # -----------------------------
    # decks
    # -----------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decks (

        player_key TEXT PRIMARY KEY,

        deck_url TEXT

    )
    """)

    # -----------------------------
    # deck_cards
    # -----------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deck_cards (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        player_key TEXT,

        quantity INTEGER,

        card_name TEXT,

        card_type TEXT,

        set_code TEXT,

        card_number TEXT

    )
    """)

    conn.commit()
    conn.close()


def insert_players(players):
    """
    Insert a list of Player objects into the database.
    """

    conn = get_connection()
    cursor = conn.cursor()

    player_rows = []

    for player in players:

        player_rows.append((
            player.player_key,
            player.tournament_id,
            player.first_name,
            player.last_name,
            player.country,
            player.division,
            player.standing,
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO players (

            player_key,
            tournament_id,
            first_name,
            last_name,
            country,
            division,
            standing

        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, player_rows)

    conn.commit()
    conn.close()