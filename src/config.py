"""
Project configuration.
"""

# Base URLs
BASE_URL = "https://rk9.gg"
ROSTER_URL = BASE_URL + "/roster/"
DECK_URL = BASE_URL + "/decklist/public/"

# Local folders
DATABASE_FOLDER = "database"
RAW_FOLDER = "raw"
EXPORT_FOLDER = "exports"

# SQLite database
DATABASE_NAME = "pokemon.db"

# HTTP request headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    )
}