"""
Main entry point for the Pokemon TCG analytics project.
"""

from src.database import create_database
from src.importer import sync_database
from src.classifier_sync import sync_classifications


def main():
    """
    Run the full ETL pipeline.
    """

    create_database()

    sync_database()

    sync_classifications()


if __name__ == "__main__":
    main()