"""
Main script for testing the RK9 roster parser.
"""

from src.roster import (
    download_roster,
    get_player_rows,
    parse_player,
)

TOURNAMENT_ID = "TU01w1D52rjGebrE8szS"


def main():
    soup = download_roster(TOURNAMENT_ID)

    rows = get_player_rows(soup)

    print(f"Found {len(rows)} players\n")

    player, deck = parse_player(rows[0], TOURNAMENT_ID)

    print("PLAYER")
    print(player)

    print("\nDECK")
    print(deck)


if __name__ == "__main__":
    main()