"""
Tournament importer.
"""

from src.metadata import load_tournaments
from src.database import (
    get_connection,
    tournament_exists,
    insert_tournament,
    insert_players,
    insert_decks,
    insert_cards,
)
from src.models import Player, Deck
from src.roster import parse_roster
from src.scraper import parse_all_decks


def _stored_decks(tournament_id):
    """Load stored player/deck pairs for a resumable tournament import."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.player_key, p.first_name, p.last_name, p.country,
               p.division, p.standing, d.deck_url
        FROM players p
        INNER JOIN decks d ON d.player_key = p.player_key
        WHERE p.tournament_id = ?
        ORDER BY p.standing, p.player_key
        """,
        (tournament_id,),
    ).fetchall()
    conn.close()

    players = []
    decks = []
    for row in rows:
        player_key, first_name, last_name, country, division, standing, deck_url = row
        players.append(
            Player(
                player_key=player_key,
                tournament_id=tournament_id,
                first_name=first_name,
                last_name=last_name,
                country=country,
                division=division,
                standing=standing,
            )
        )
        decks.append(Deck(player_key=player_key, deck_url=deck_url))
    return players, decks


def _completed_card_players(tournament_id):
    """Return players whose cards are already stored for this tournament."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT dc.player_key
        FROM deck_cards dc
        INNER JOIN players p ON p.player_key = dc.player_key
        WHERE p.tournament_id = ?
        """,
        (tournament_id,),
    ).fetchall()
    conn.close()
    return {row[0] for row in rows}


def _tournament_counts(tournament_id):
    """Return stored deck and parsed-card player counts."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT d.player_key), COUNT(DISTINCT dc.player_key)
        FROM players p
        LEFT JOIN decks d ON d.player_key = p.player_key
        LEFT JOIN deck_cards dc ON dc.player_key = p.player_key
        WHERE p.tournament_id = ?
        """,
        (tournament_id,),
    ).fetchone()
    conn.close()
    return row


def sync_database():
    """
    Synchronize the SQLite database with metadata.xlsx.
    """

    tournaments = load_tournaments()

    print()
    print("=" * 60)
    print("SYNC DATABASE")
    print("=" * 60)

    for _, tournament in tournaments.iterrows():

        tournament_id = tournament["tournament_id"]
        tournament_name = tournament["tournament_name"]

        if tournament_exists(tournament_id):
            stored_decks, parsed_cards = _tournament_counts(tournament_id)
            if stored_decks and stored_decks == parsed_cards:
                print(f"[OK] {tournament_name} already imported")
                print()
                continue

            print(f"[RESUME] {tournament_name}")
            players, decks = _stored_decks(tournament_id)
            if not decks:
                # A previous run may have inserted tournament metadata before
                # failing while downloading/parsing the roster.
                players, decks = parse_roster(tournament_id)
                print(f"  Players : {len(players)}")
                print(f"  Decks   : {len(decks)}")
                insert_players(players)
                insert_decks(decks)
                print("  Players inserted")
                print("  Decks inserted")
        else:
            print(f"+ Importing {tournament_name}")
            insert_tournament(tournament)
            print("  Tournament metadata inserted")
            players, decks = parse_roster(tournament_id)
            print(f"  Players : {len(players)}")
            print(f"  Decks   : {len(decks)}")
            insert_players(players)
            insert_decks(decks)
            print("  Players inserted")
            print("  Decks inserted")

        completed_players = _completed_card_players(tournament_id)
        remaining = len(players) - len(completed_players)
        print(f"  Decks remaining for card parsing: {remaining}")

        def save_batch(cards):
            insert_cards(cards)
            print(f"  Saved {len(cards)} card rows")

        parse_all_decks(
            players,
            decks,
            skip_player_keys=completed_players,
            workers=12,
            batch_size=50,
            on_batch=save_batch,
        )
        print("  Cards synchronized")
        print()

    print("=" * 60)
    print("DATABASE SYNC COMPLETE")
    print("=" * 60)
