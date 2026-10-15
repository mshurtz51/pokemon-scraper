"""
Card catalog ingestion and deck-card identity resolution.

The catalog uses the public TCGdex API for structured card metadata and stores
the corresponding official Pokémon card-page and image URLs. Pokedata is not
used as a source of truth.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import sqlite3
import time

import requests

from src.config import DATABASE_NAME, HEADERS
from src.database import create_database


TCGDEX_API_URL = "https://api.tcgdex.net/v2/en"
OFFICIAL_CARD_URL = (
    "https://www.pokemon.com/us/pokemon-tcg/pokemon-cards/"
    "series/{set_code}/{card_number}/"
)
OFFICIAL_IMAGE_URL = (
    "https://assets.pokemon.com/static-assets/content-assets/cms2/img/"
    "cards/web/{display_set}/{display_set}_EN_{card_number}.png"
)

# RK9 currently uses MEG for the English Mega Evolution set while official
# pages and structured catalog APIs use me01.
SET_CODE_ALIASES = {
    "MEG": "me01",
    "ME01": "me01",
    "SVI": "sv01",
    "PAL": "sv02",
    "OBF": "sv03",
    "MEW": "sv03.5",
    "PAR": "sv04",
    "PAF": "sv04.5",
    "TEF": "sv05",
    "TWM": "sv06",
    "SFA": "sv06.5",
    "SCR": "sv07",
    "SSP": "sv08",
    "PRE": "sv08.5",
    "JTG": "sv09",
    "DRI": "sv10",
    "BLK": "sv10.5b",
    "WHT": "sv10.5w",
}

OFFICIAL_SET_CODES = {
    "me01": "ME01",
    "me02": "ME02",
    "me02.5": "ME02PT5",
    "me03": "ME03",
    "me04": "ME04",
    "me05": "ME05",
    "sv01": "SV01",
    "sv02": "SV02",
    "sv03": "SV03",
    "sv03.5": "SV3PT5",
    "sv04": "SV04",
    "sv04.5": "SV4PT5",
    "sv05": "SV05",
    "sv06": "SV06",
    "sv06.5": "SV6PT5",
    "sv07": "SV07",
    "sv08": "SV08",
    "sv08.5": "SV8PT5",
    "sv09": "SV09",
    "sv10": "SV10",
    "sv10.5b": "SV10.5B",
    "sv10.5w": "SV10.5W",
}


def normalize_set_code(set_code):
    """Return the catalog set code for an RK9 or catalog set code."""

    normalized = str(set_code).strip()

    return SET_CODE_ALIASES.get(normalized.upper(), normalized.lower())


def _display_set_code(set_code):
    """Return the uppercase set code used by official image filenames."""

    return OFFICIAL_SET_CODES.get(set_code, set_code.upper())


def _official_series_code(set_code):
    """Return the series path used by official card pages."""

    return {
        "me02.5": "me02pt5",
        "sv03.5": "sv3pt5",
        "sv04.5": "sv4pt5",
        "sv06.5": "sv6pt5",
        "sv08.5": "sv8pt5",
    }.get(set_code, set_code)


def _card_number(card_number):
    """Normalize a card number to the three-digit catalog form."""

    value = str(card_number).strip()

    if value.isdigit():
        return value.zfill(3)

    return value


def _request_json(url):
    """Fetch one JSON payload with the project's standard headers."""

    for attempt in range(4):
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            return response.json()

        if attempt == 3:
            response.raise_for_status()

        time.sleep(2 ** attempt)

    raise RuntimeError(f"Unable to fetch JSON: {url}")


def fetch_set_summary(set_code="me01"):
    """Fetch the card summary for one set from TCGdex."""

    normalized_set = normalize_set_code(set_code)

    return _request_json(f"{TCGDEX_API_URL}/sets/{normalized_set}")


def discover_set_codes(block):
    """Return expansion set IDs for the requested card block."""

    normalized_block = block.strip().lower()
    all_sets = _request_json(f"{TCGDEX_API_URL}/sets")

    if normalized_block == "me":
        prefixes = ("me",)
        excluded = {"mee", "mep"}
    elif normalized_block == "sv":
        prefixes = ("sv",)
        excluded = {"sve", "svp"}
    else:
        raise ValueError("block must be 'me' or 'sv'")

    return [
        card_set["id"]
        for card_set in all_sets
        if card_set["id"].startswith(prefixes)
        and card_set["id"] not in excluded
    ]


def fetch_card(card_id):
    """Fetch detailed metadata for one catalog card."""

    return _request_json(f"{TCGDEX_API_URL}/cards/{card_id}")


def _card_row(card, set_code):
    """Convert one TCGdex card response to a database row."""

    card_number = _card_number(card["localId"])
    display_set = _display_set_code(set_code)

    return {
        "card_id": card["id"],
        "language": "en",
        "set_code": set_code,
        "card_number": card_number,
        "card_name": card["name"],
        "category": card.get("category"),
        "rarity": card.get("rarity"),
        "card_types": json.dumps(card.get("types", [])),
        "stage": card.get("stage"),
        "hp": str(card["hp"]) if card.get("hp") is not None else None,
        "official_card_url": OFFICIAL_CARD_URL.format(
            set_code=_official_series_code(set_code),
            card_number=int(card_number) if card_number.isdigit() else card_number,
        ),
        "official_image_url": OFFICIAL_IMAGE_URL.format(
            display_set=display_set,
            card_number=int(card_number) if card_number.isdigit() else card_number,
        ),
        "tcgdex_image_url": card.get("image"),
        "metadata_source": "https://api.tcgdex.net/v2/en",
        "image_source": "https://www.pokemon.com/us/pokemon-tcg/pokemon-cards",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_set_cards(set_code="me01", workers=8, details=True):
    """Fetch all cards for one set, optionally fetching detail payloads."""

    normalized_set = normalize_set_code(set_code)
    summary = fetch_set_summary(normalized_set)
    cards = summary.get("cards", [])

    if not details:
        return [_card_row(card, normalized_set) for card in cards]

    if workers <= 1:
        details = [fetch_card(card["id"]) for card in cards]
    else:
        details = []

        with ThreadPoolExecutor(max_workers=workers) as executor:

            futures = [
                executor.submit(fetch_card, card["id"])
                for card in cards
            ]

            for future in as_completed(futures):
                details.append(future.result())

    return [_card_row(card, normalized_set) for card in details]


def upsert_cards(rows, database_path=DATABASE_NAME):
    """Upsert catalog rows into the main database."""

    create_database(database_path)
    connection = sqlite3.connect(database_path)

    try:
        connection.executemany(
            """
            INSERT INTO cards (
                card_id,
                language,
                set_code,
                card_number,
                card_name,
                category,
                rarity,
                card_types,
                stage,
                hp,
                official_card_url,
                official_image_url,
                tcgdex_image_url,
                metadata_source,
                image_source,
                updated_at
            )
            VALUES (
                :card_id,
                :language,
                :set_code,
                :card_number,
                :card_name,
                :category,
                :rarity,
                :card_types,
                :stage,
                :hp,
                :official_card_url,
                :official_image_url,
                :tcgdex_image_url,
                :metadata_source,
                :image_source,
                :updated_at
            )
            ON CONFLICT(card_id) DO UPDATE SET
                card_name = excluded.card_name,
                category = excluded.category,
                rarity = excluded.rarity,
                card_types = excluded.card_types,
                stage = excluded.stage,
                hp = excluded.hp,
                official_card_url = excluded.official_card_url,
                official_image_url = excluded.official_image_url,
                tcgdex_image_url = excluded.tcgdex_image_url,
                metadata_source = excluded.metadata_source,
                image_source = excluded.image_source,
                updated_at = excluded.updated_at
            """,
            rows,
        )

        connection.commit()
    finally:
        connection.close()


def link_deck_cards(set_code="me01", database_path=DATABASE_NAME):
    """Backfill catalog card IDs onto matching RK9 deck-card rows."""

    normalized_set = normalize_set_code(set_code)
    source_set_codes = [
        source_code
        for source_code, catalog_code in SET_CODE_ALIASES.items()
        if catalog_code == normalized_set
    ]

    if not source_set_codes:
        source_set_codes = [normalized_set.upper()]

    connection = sqlite3.connect(database_path)

    try:
        cursor = connection.execute(
            """
            UPDATE deck_cards
            SET card_id = ? || printf('%03d', CAST(card_number AS INTEGER))
            WHERE UPPER(set_code) IN ({placeholders})
              AND card_number GLOB '[0-9]*'
            """.format(placeholders=", ".join("?" for _ in source_set_codes)),
            (normalized_set + "-", *source_set_codes),
        )

        connection.commit()

        return cursor.rowcount
    finally:
        connection.close()


def ingest_set(
    set_code="me01",
    workers=8,
    database_path=DATABASE_NAME,
    details=True,
):
    """Fetch, store, and link one set, returning the ingestion counts."""

    rows = fetch_set_cards(
        set_code=set_code,
        workers=workers,
        details=details,
    )
    upsert_cards(rows, database_path=database_path)
    linked_rows = link_deck_cards(set_code=set_code, database_path=database_path)

    return {
        "set_code": normalize_set_code(set_code),
        "catalog_cards": len(rows),
        "linked_deck_cards": linked_rows,
    }


def ingest_block(
    block,
    workers=8,
    database_path=DATABASE_NAME,
    details=False,
):
    """Ingest every expansion in a Mega Evolution or Scarlet & Violet block."""

    results = []

    for set_code in discover_set_codes(block):
        print(f"Ingesting {set_code}...")
        results.append(
            ingest_set(
                set_code=set_code,
                workers=workers,
                database_path=database_path,
                details=details,
            )
        )

    return results
