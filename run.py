"""
Main entry point for the Pokemon TCG analytics project.
"""

from src.database import create_database
from src.importer import sync_database


def main():
    """
    Run the full ETL pipeline.
    """

    create_database()

    sync_database()


if __name__ == "__main__":
    main()