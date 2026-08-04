"""
Manual QA tests for the RK9 scraper.
"""

from src.roster import (
    fetch_roster,
    get_player_rows,
    parse_roster,
)

TOURNAMENT_ID = "TU01w1D52rjGebrE8szS"


def main():

    # Fetch the raw roster and count HTML rows
    soup = fetch_roster(TOURNAMENT_ID)
    rows = get_player_rows(soup)

    # Parse the roster into objects
    players, decks = parse_roster(TOURNAMENT_ID)

    print("=" * 60)
    print("RK9 ROSTER QA")
    print("=" * 60)

    print(f"HTML rows found : {len(rows)}")
    print(f"Players parsed  : {len(players)}")
    print(f"Decks parsed    : {len(decks)}")

    if len(rows) == len(players) == len(decks):
        print("\n✓ Counts match")
    else:
        print("\n✗ Count mismatch")

    print("\n" + "=" * 60)
    print("FIRST PLAYER")
    print("=" * 60)
    print(players[0])

    print("\nFIRST DECK")
    print("=" * 60)
    print(decks[0])

    print("\n" + "=" * 60)
    print("PLAYER #300")
    print("=" * 60)
    print(players[299])

    print("\nDECK #300")
    print("=" * 60)
    print(decks[299])

    print("\n" + "=" * 60)
    print("LAST PLAYER")
    print("=" * 60)
    print(players[-1])

    print("\nLAST DECK")
    print("=" * 60)
    print(decks[-1])


if __name__ == "__main__":
    main()
