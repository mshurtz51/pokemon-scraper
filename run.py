"""
Main script for testing the RK9 roster parser.
"""

from src.roster import parse_roster

TOURNAMENT_ID = "TU01w1D52rjGebrE8szS"


def main():

    players, decks = parse_roster(TOURNAMENT_ID)

    print(f"Players parsed: {len(players)}")
    print(f"Decks parsed:   {len(decks)}")

    print("\nFirst player:")
    print(players[0])

    print("\nFirst deck:")
    print(decks[0])


if __name__ == "__main__":
    main()