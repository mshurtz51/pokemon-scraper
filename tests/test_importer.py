"""
QA test for the tournament importer.
"""

import os
import sys

# Allow imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import create_database
from src.importer import sync_database


def main():

    create_database()

    print("=" * 60)
    print("SYNC DATABASE")
    print("=" * 60)

    sync_database()

    print()
    print("=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()