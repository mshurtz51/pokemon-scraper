"""
SQLite database functions.
"""

import sqlite3

from src.config import DATABASE_NAME


def get_connection():
    """
    Return a connection to the SQLite database.
    """

    return sqlite3.connect(str(DATABASE_NAME))


def create_database():
    """
    Create all database tables if they do not exist.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (

            tournament_id TEXT PRIMARY KEY,

            tournament_name TEXT,

            season INTEGER,

            game TEXT,

            format TEXT,

            event_type TEXT,

            city TEXT,

            state_province TEXT,

            country TEXT,

            start_date TEXT,

            begin_set TEXT,

            end_set TEXT,

            notes TEXT

        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (

            player_key TEXT PRIMARY KEY,

            tournament_id TEXT,

            first_name TEXT,

            last_name TEXT,

            country TEXT,

            division TEXT,

            standing INTEGER,

            overall TEXT,

            variant TEXT,

            matched INTEGER,

            score REAL

        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decks (

            player_key TEXT PRIMARY KEY,

            deck_url TEXT

        )
    """)

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

    #
    # Add classification columns for existing databases.
    #

    cursor.execute("PRAGMA table_info(players)")

    existing_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    new_columns = {

        "overall": "TEXT",

        "variant": "TEXT",

        "matched": "INTEGER",

        "score": "REAL",

    }

    for column, datatype in new_columns.items():

        if column not in existing_columns:

            cursor.execute(
                f"""
                ALTER TABLE players
                ADD COLUMN {column} {datatype}
                """
            )

    conn.commit()
    conn.close()


def tournament_exists(tournament_id):
    """
    Return True if a tournament already exists.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM tournaments
        WHERE tournament_id = ?
        LIMIT 1
        """,
        (tournament_id,),
    )

    exists = cursor.fetchone() is not None

    conn.close()

    return exists


def insert_tournament(tournament):
    """
    Insert one tournament into the database.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO tournaments (

            tournament_id,
            tournament_name,
            season,
            game,
            format,
            event_type,
            city,
            state_province,
            country,
            start_date,
            begin_set,
            end_set,
            notes

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tournament["tournament_id"],
            tournament["tournament_name"],
            tournament["season"],
            tournament["game"],
            tournament["format"],
            tournament["event_type"],
            tournament["city"],
            tournament["state_province"],
            tournament["country"],
            str(tournament["start_date"]),
            tournament["begin_set"],
            tournament["end_set"],
            tournament["notes"],
        ),
    )

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

    cursor.executemany(
        """
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
        """,
        player_rows,
    )

    conn.commit()
    conn.close()


def insert_decks(decks):
    """
    Insert a list of Deck objects into the database.
    """

    conn = get_connection()
    cursor = conn.cursor()

    deck_rows = []

    for deck in decks:

        deck_rows.append((
            deck.player_key,
            deck.deck_url,
        ))

    cursor.executemany(
        """
        INSERT OR REPLACE INTO decks (

            player_key,
            deck_url

        )
        VALUES (?, ?)
        """,
        deck_rows,
    )

    conn.commit()
    conn.close()


def insert_cards(cards):
    """
    Insert a list of DeckCard objects into the database.
    """

    conn = get_connection()
    cursor = conn.cursor()

    card_rows = []

    for card in cards:

        card_rows.append((
            card.player_key,
            card.quantity,
            card.card_name,
            card.card_type,
            card.set_code,
            card.card_number,
        ))

    cursor.executemany(
        """
        INSERT INTO deck_cards (

            player_key,
            quantity,
            card_name,
            card_type,
            set_code,
            card_number

        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        card_rows,
    )

    conn.commit()
    conn.close()