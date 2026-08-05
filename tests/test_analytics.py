"""
QA test for analytics functions.
"""

import os
import sys

# Allow imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics import top_cards
from src.config import DATABASE_NAME


def main():

    print("=" * 60)
    print("TOP 25 MOST PLAYED CARDS")
    print("=" * 60)

    print("Current working directory:")
    print(os.getcwd())

    print()

    print("Database path:")
    print(os.path.abspath(DATABASE_NAME))

    print()

    print("Database exists:")
    print(os.path.exists(DATABASE_NAME))

    print()

    df = top_cards(25)

    print(df)


if __name__ == "__main__":
    main()
