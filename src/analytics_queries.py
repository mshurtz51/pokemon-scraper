"""
Database queries used by analytics.
"""

import sqlite3

import pandas as pd

from src.config import DATABASE_NAME


def get_connection():
    """
    Return a database connection.
    """

    return sqlite3.connect(str(DATABASE_NAME))


def get_tournaments():
    """
    Return all tournaments.

    Returns
    -------
    pandas.DataFrame
    """

    conn = get_connection()

    query = """
        SELECT

            tournament_id,
            tournament_name,
            start_date

        FROM tournaments

        ORDER BY start_date
    """

    df = pd.read_sql_query(
        query,
        conn,
    )

    conn.close()

    return df


def get_classified_players(tournament_id):
    """
    Return classified Masters players for one tournament.

    Parameters
    ----------
    tournament_id : str

    Returns
    -------
    pandas.DataFrame
    """

    conn = get_connection()

    query = """
        SELECT

            player_key,
            first_name,
            last_name,
            country,
            standing,
            overall,
            variant,
            matched,
            score

        FROM players

        WHERE
            tournament_id = ?
            AND division = 'Masters'

        ORDER BY standing
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(tournament_id,),
    )

    conn.close()

    return df

def get_deck(player_key):
    """
    Return one player's deck.

    Parameters
    ----------
    player_key : str

    Returns
    -------
    pandas.DataFrame
    """

    conn = get_connection()

    query = """
        SELECT

            quantity,
            card_name,
            card_type

        FROM deck_cards

        WHERE player_key = ?

        ORDER BY
            card_type,
            quantity DESC,
            card_name
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(player_key,),
    )

    conn.close()

    return df