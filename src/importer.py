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
from src.pairings import resolve_player, scrape_tournament_pairings
from src.pairing_database import (
    create_pairing_database,
    insert_pairing_matches,
    tournament_pairings_exist,
)


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


def _stored_roster(tournament_id):
    """Load the stored roster in the shape used by pairing resolution."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT player_key, first_name, last_name, country, division
        FROM players
        WHERE tournament_id = ?
        ORDER BY player_key
        """,
        (tournament_id,),
    ).fetchall()
    conn.close()

    return [
        {
            "player_key": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "country": row[3] or "",
            "division": row[4],
        }
        for row in rows
    ]


def sync_pairings(tournament_id):
    """Import all currently published RK9 pairings for one tournament."""
    if tournament_pairings_exist(tournament_id):
        print("  Pairings already synchronized")
        return

    matches = scrape_tournament_pairings(tournament_id)
    roster = _stored_roster(tournament_id)
    roster_by_division = {}
    for player in roster:
        roster_by_division.setdefault(player["division"], []).append(player)

    resolutions = {}
    resolution_counts = {"exact": 0, "ambiguous": 0, "unmatched": 0}
    for match in matches:
        division_roster = roster_by_division.get(match.division, [])
        for side, player in (
            ("player1", match.player1),
            ("player2", match.player2),
        ):
            if player is None:
                continue
            resolution = resolve_player(player, division_roster)
            resolutions[(match.match_key, side)] = resolution
            resolution_counts[resolution.status] += 1

    insert_pairing_matches(matches, resolutions)
    print(f"  Pairings : {len(matches)} matches")
    print(
        "  Pairing player resolutions: "
        f"{resolution_counts['exact']} exact, "
        f"{resolution_counts['ambiguous']} ambiguous, "
        f"{resolution_counts['unmatched']} unmatched"
    )


def sync_database():
    """
    Synchronize the SQLite database with metadata.xlsx.
    """

    tournaments = load_tournaments()
    create_pairing_database()

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
                sync_pairings(tournament_id)
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

        # Pairings depend on the roster identity and division, not on card
        # parsing. Store them now so a later card-parser retry does not leave
        # the tournament without its round data.
        sync_pairings(tournament_id)

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
