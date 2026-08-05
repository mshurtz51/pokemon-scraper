"""
Project configuration.
"""

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Base URLs
BASE_URL = "https://rk9.gg"
ROSTER_URL = BASE_URL + "/roster/"
DECK_URL = BASE_URL + "/decklist/public/"

# Local folders
DATABASE_FOLDER = PROJECT_ROOT / "database"
RAW_FOLDER = PROJECT_ROOT / "raw"
EXPORT_FOLDER = PROJECT_ROOT / "exports"

# Create folders if needed
DATABASE_FOLDER.mkdir(exist_ok=True)
RAW_FOLDER.mkdir(exist_ok=True)
EXPORT_FOLDER.mkdir(exist_ok=True)

# SQLite database
DATABASE_NAME = DATABASE_FOLDER / "pokemon.db"

# HTTP request headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    )
}