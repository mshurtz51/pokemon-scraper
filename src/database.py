import sqlite3


def create_database(db_name="database/pokemon.db"):

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Players(
        player_id TEXT,
        tournament_id TEXT,
        first_name TEXT,
        last_name TEXT,
        country TEXT,
        division TEXT,
        standing INTEGER,
        deck_url TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS DeckCards(
        player_id TEXT,
        card_name TEXT,
        quantity INTEGER,
        card_type TEXT,
        set_number TEXT,
        language TEXT
    )
    """)

    conn.commit()

    return conn