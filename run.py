"""
Main entry point for the Pokemon TCG analytics project.
"""

from src.database import create_database
from src.importer import sync_database
from src.classifier_sync import sync_classifications
from src.matchups import refresh_day_two_fields, refresh_matchups


def main():
    """
    Run the full ETL pipeline.
    """

    create_database()

    sync_database()

    sync_classifications()

    day_two_counts = refresh_day_two_fields()
    print(
        f"DAY 2 READY: {day_two_counts['player_flags']} player flags across "
        f"{day_two_counts['pairings']} pairing records"
    )

    matchup_counts = refresh_matchups()
    print(
        f"MATCHUPS READY: {matchup_counts['eligible']} eligible of "
        f"{matchup_counts['records']} pairing records"
    )


if __name__ == "__main__":
    main()
