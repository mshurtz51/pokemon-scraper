"""
Tournament importer.
"""

from src.metadata import load_tournaments
from src.database import (
    tournament_exists,
    insert_tournament,
    insert_players,
    insert_decks,
    insert_cards,
)
from src.roster import parse_roster
from src.scraper import parse_all_decks


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

            print(f"✓ {tournament_name} already imported")
            print()

            continue

        print(f"+ Importing {tournament_name}")

        # Tournament metadata
        insert_tournament(tournament)
        print("  Tournament metadata inserted")

        # Players & Decks
        players, decks = parse_roster(tournament_id)

        print(f"  Players : {len(players)}")
        print(f"  Decks   : {len(decks)}")

        insert_players(players)
        insert_decks(decks)

        print("  Players inserted")
        print("  Decks inserted")

        # Cards
        cards = parse_all_decks(players, decks)

        print(f"  Cards   : {len(cards)}")

        insert_cards(cards)

        print("  Cards inserted")
        print()

    print("=" * 60)
    print("DATABASE SYNC COMPLETE")
    print("=" * 60)