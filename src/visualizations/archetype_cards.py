"""Representative-card contact sheet for archetype and variant metadata."""

from io import BytesIO
from pathlib import Path
import sqlite3

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import requests

from src.config import DATABASE_NAME, PROJECT_ROOT


METADATA_FILE = PROJECT_ROOT / "metadata" / "metadata.xlsx"
OUTPUT_FOLDER = PROJECT_ROOT / "src" / "visualizations" / "output" / "visualizations"
CARD_CACHE_FOLDER = PROJECT_ROOT / "assets" / "cards" / "cache"

REQUIRED_COLUMNS = {
    "overall_archetype",
    "variant",
    "representative_card_id",
    "representative_card_id_2",
}


def normalize_card_id(card_id):
    """Normalize IDs such as ``sv09-9`` to the catalog form ``sv09-009``."""

    if pd.isna(card_id):
        return None

    value = str(card_id).strip()

    if "-" not in value:
        return value

    set_code, number = value.rsplit("-", 1)

    if number.isdigit():
        return f"{set_code.lower()}-{number.zfill(3)}"

    return value.lower()


def load_archetype_cards(metadata_file=METADATA_FILE):
    """Load and validate the representative-card worksheet."""

    frame = pd.read_excel(
        metadata_file,
        sheet_name="archetype_cards",
    )

    frame = frame.loc[:, ~frame.columns.astype(str).str.startswith("Unnamed")]
    missing_columns = REQUIRED_COLUMNS - set(frame.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"archetype_cards is missing required columns: {missing}"
        )

    for column in [
        "overall_archetype",
        "variant",
        "representative_card_id",
        "representative_card_id_2",
    ]:
        frame[column] = frame[column].apply(normalize_card_id)

    return frame


def load_catalog_cards(database_path=DATABASE_NAME):
    """Load catalog card metadata and image URLs."""

    connection = sqlite3.connect(database_path)

    try:
        return pd.read_sql_query(
            """
            SELECT
                card_id,
                card_name,
                official_image_url,
                tcgdex_image_url
            FROM cards
            """,
            connection,
        )
    finally:
        connection.close()


def resolve_cards(archetype_cards, catalog_cards):
    """Attach catalog rows and return unresolved IDs separately."""

    catalog = catalog_cards.set_index("card_id").to_dict("index")
    resolved = []
    missing = []

    for _, row in archetype_cards.iterrows():
        output = row.to_dict()
        output["cards"] = []

        for column in [
            "representative_card_id",
            "representative_card_id_2",
        ]:
            card_id = row[column]

            if pd.isna(card_id) or not str(card_id).strip():
                continue

            card = catalog.get(card_id)

            if card is None:
                missing.append({
                    "overall_archetype": row["overall_archetype"],
                    "variant": row["variant"],
                    "card_id": card_id,
                })
                continue

            output["cards"].append(card | {"card_id": card_id})

        resolved.append(output)

    return resolved, pd.DataFrame(missing)


def _load_image(card):
    """Load one card image from the local cache or catalog URLs."""

    CARD_CACHE_FOLDER.mkdir(parents=True, exist_ok=True)
    cache_path = CARD_CACHE_FOLDER / f"{card['card_id'].replace('/', '_')}.png"

    if cache_path.exists():
        try:
            return mpimg.imread(cache_path)
        except Exception:
            cache_path.unlink(missing_ok=True)

    for url in [card.get("official_image_url"), card.get("tcgdex_image_url")]:
        if not url:
            continue

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            cache_path.write_bytes(response.content)
            return mpimg.imread(BytesIO(response.content), format="png")
        except Exception:
            continue

    return None


def _draw_entry(cell, entry):
    """Draw one archetype/variant entry with up to two cards."""

    cell.axis("off")
    cell.text(
        0.5,
        0.98,
        entry["overall_archetype"],
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="#1A1A1A",
    )
    cell.text(
        0.5,
        0.89,
        entry["variant"],
        ha="center",
        va="top",
        fontsize=10,
        color="#6B6B6B",
    )

    cards = entry["cards"]
    positions = [0.08, 0.54] if len(cards) > 1 else [0.27]
    widths = 0.38 if len(cards) > 1 else 0.46

    for card, left in zip(cards, positions):
        image = _load_image(card)
        image_ax = cell.inset_axes([left, 0.20, widths, 0.61])
        image_ax.axis("off")

        if image is None:
            image_ax.text(
                0.5,
                0.5,
                "IMAGE\nUNAVAILABLE",
                ha="center",
                va="center",
                color="#A6192E",
                fontsize=9,
                fontweight="bold",
            )
        else:
            image_ax.imshow(image)

        cell.text(
            left + widths / 2,
            0.13,
            f"{card['card_name']}\n{card['card_id']}",
            ha="center",
            va="top",
            fontsize=8,
            color="#1A1A1A",
        )


def _render_grid(entries, output_path, title, rows_per_page=None, pdf=False):
    """Render entries to a PNG or multipage PDF."""

    columns = 4
    rows_per_page = rows_per_page or len(entries)
    chunks = [
        entries[index:index + rows_per_page * columns]
        for index in range(0, len(entries), rows_per_page * columns)
    ]

    if pdf:
        document = PdfPages(output_path)
    else:
        document = None

    try:
        for page_entries in chunks:
            page_rows = max(1, (len(page_entries) + columns - 1) // columns)
            figure, axes = plt.subplots(
                page_rows,
                columns,
                figsize=(16, max(4.5, page_rows * 3.6)),
                squeeze=False,
            )
            axes = axes.ravel()

            figure.suptitle(
                title,
                fontsize=22,
                fontweight="bold",
                x=0.05,
                ha="left",
            )

            for cell, entry in zip(axes, page_entries):
                _draw_entry(cell, entry)

            for cell in axes[len(page_entries):]:
                cell.axis("off")

            figure.tight_layout(rect=[0, 0, 1, 0.95])

            if document is not None:
                document.savefig(figure, bbox_inches="tight")
            else:
                figure.savefig(output_path, dpi=180, bbox_inches="tight")

            plt.close(figure)
    finally:
        if document is not None:
            document.close()


def create_archetype_card_contact_sheet(
    metadata_file=METADATA_FILE,
    database_path=DATABASE_NAME,
    output_folder=OUTPUT_FOLDER,
):
    """Create the full PNG/PDF contact sheet and return validation details."""

    metadata = load_archetype_cards(metadata_file)
    catalog = load_catalog_cards(database_path)
    entries, missing = resolve_cards(metadata, catalog)
    image_failures = []

    for entry in entries:
        for card in entry["cards"]:
            if _load_image(card) is None:
                image_failures.append({
                    "overall_archetype": entry["overall_archetype"],
                    "variant": entry["variant"],
                    "card_id": card["card_id"],
                    "card_name": card["card_name"],
                })

    output_folder.mkdir(parents=True, exist_ok=True)
    title = "Archetype and Variant Representative Cards"

    _render_grid(
        entries,
        output_folder / "archetype_cards_contact_sheet.png",
        title,
    )
    _render_grid(
        entries,
        output_folder / "archetype_cards_contact_sheet.pdf",
        title,
        rows_per_page=5,
        pdf=True,
    )

    return {
        "archetype_rows": len(entries),
        "configured_card_ids": int(
            metadata[
                ["representative_card_id", "representative_card_id_2"]
            ]
            .notna()
            .sum()
            .sum()
        ),
        "missing_card_ids": missing,
        "image_failures": pd.DataFrame(image_failures),
        "png_path": output_folder / "archetype_cards_contact_sheet.png",
        "pdf_path": output_folder / "archetype_cards_contact_sheet.pdf",
    }
