
"""
Analytics functions for the Pokemon Scraper project.
"""

import sqlite3
import pandas as pd

from src.config import DATABASE_NAME


def top_cards(limit=25):
    """
    Return the most played cards by total copies.

    Parameters
    ----------
    limit : int
        Number of cards to return.

    Returns
    -------
    pandas.DataFrame
    """

    conn = sqlite3.connect(DATABASE_NAME)

    query = """
        SELECT
            card_name,
            SUM(quantity) AS copies,
            COUNT(DISTINCT player_key) AS decks
        FROM deck_cards
        GROUP BY card_name
        ORDER BY copies DESC
        LIMIT ?
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(limit,)
    )

    conn.close()

    return df