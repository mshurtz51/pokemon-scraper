"""
QA test for metadata.xlsx.
"""

import os
import sys

# Allow imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.metadata import load_tournaments, load_sets


def main():

    tournaments = load_tournaments()
    sets = load_sets()

    print("=" * 60)
    print("TOURNAMENTS")
    print("=" * 60)

    print(f"Rows: {len(tournaments)}")
    print()
    print(tournaments)

    print()

    print("=" * 60)
    print("SETS")
    print("=" * 60)

    print(f"Rows: {len(sets)}")
    print()
    print(sets)


if __name__ == "__main__":
    main()