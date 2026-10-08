"""
Core Cards visualization.

Groups every card in a selected Masters archetype or variant by its inclusion
tier, using the established core/common/flex/tech definitions.
"""

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analytics_queries import get_archetype_cards, get_tournaments
from src.visualizations.chart_style import (
    BACKGROUND_COLOR,
    BRAND_COLOR,
    BRAND_DARK,
    BORDER_COLOR,
    SECONDARY_TEXT_COLOR,
    TEXT_COLOR,
    save_chart,
)


OUTPUT_DIRECTORY = (
    Path(__file__).resolve().parent
    / "output"
    / "visualizations"
)


TIER_DEFINITIONS = (
    ("100% Core", 100, 101, "#4F8A55"),
    ("95–99% Core", 95, 100, "#649A63"),
    ("80–94% Common", 80, 95, "#9A801D"),
    ("50–79% Flex", 50, 80, "#B47A17"),
    ("20–49% Tech", 20, 50, BRAND_COLOR),
    ("<20% Rare Tech", 0, 20, "#8B4A5A"),
)


SECTION_COLORS = {
    "pokemon": "#5A8F4D",
    "trainer": "#4F73A8",
    "energy": "#B47A17",
    "other": SECONDARY_TEXT_COLOR,
}


def select_tournament():
    """Prompt for one tournament."""
    tournaments = get_tournaments()

    print("\nAvailable Tournaments:\n")
    for index, row in tournaments.iterrows():
        print(f"{index + 1}. {row['tournament_name']}")

    while True:
        try:
            choice = int(input("\nSelect tournament: "))
            if 1 <= choice <= len(tournaments):
                row = tournaments.iloc[choice - 1]
                return row["tournament_id"], row["tournament_name"]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(tournaments)}.")


def select_grouping():
    """Prompt for overall archetype or a specific variant."""
    print("\nSelect deck grouping:\n")
    print("1. Overall Archetype")
    print("2. Variant")

    while True:
        try:
            choice = int(input("\nSelect grouping: "))
            if choice in (1, 2):
                return "overall" if choice == 1 else "variant"
        except ValueError:
            pass
        print("Please enter 1 or 2.")


def select_archetype(df):
    """Prompt for an archetype."""
    archetypes = sorted(df["overall"].dropna().unique())

    print("\nAvailable Archetypes:\n")
    for index, archetype in enumerate(archetypes, start=1):
        print(f"{index}. {archetype}")

    while True:
        try:
            choice = int(input("\nSelect archetype: "))
            if 1 <= choice <= len(archetypes):
                return archetypes[choice - 1]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(archetypes)}.")


def select_variant(df):
    """Prompt for a variant from the selected archetype."""
    variants = sorted(df["variant"].dropna().unique())

    print("\nAvailable Variants:\n")
    for index, variant in enumerate(variants, start=1):
        print(f"{index}. {variant}")

    while True:
        try:
            choice = int(input("\nSelect variant: "))
            if 1 <= choice <= len(variants):
                return variants[choice - 1]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(variants)}.")


def build_report(df):
    """Build the established core-card metrics."""
    if df.empty:
        return pd.DataFrame()

    total_decks = df["player_key"].nunique()
    report = (
        df.groupby(["card_name", "card_type"], dropna=False)
        .agg(
            Decks=("player_key", "nunique"),
            Average_Copies=("quantity", "mean"),
        )
        .reset_index()
    )
    report["Inclusion"] = report["Decks"] / total_decks * 100
    report["tier_index"] = report["Inclusion"].apply(_tier_index)
    report["type_index"] = report["card_type"].map(
        {"pokemon": 0, "trainer": 1, "energy": 2}
    ).fillna(3)
    return report.sort_values(
        ["tier_index", "type_index", "Inclusion", "Average_Copies", "card_name"],
        ascending=[True, True, False, False, True],
    ).reset_index(drop=True)


def _tier_index(value):
    for index, (_, minimum, maximum, _) in enumerate(TIER_DEFINITIONS):
        if minimum <= value < maximum:
            return index
    return len(TIER_DEFINITIONS) - 1


def _tier_label(value):
    return TIER_DEFINITIONS[_tier_index(value)][0]


def _display_group_name(archetype, variant):
    if variant is None or variant == "Default":
        return archetype
    return f"{archetype} — {variant}"


def _section_name(card_type):
    return {
        "pokemon": "Pokémon",
        "trainer": "Trainer",
        "energy": "Energy",
    }.get(card_type, "Other")


def _draw_tile(fig, row, x, y, width, height, tier_color):
    if not hasattr(fig, "_core_tile_boxes"):
        fig._core_tile_boxes = []
    fig._core_tile_boxes.append((x, y, width, height))

    card_name = textwrap.fill(
        textwrap.shorten(str(row["card_name"]), width=28, placeholder="…"),
        width=17,
        break_long_words=False,
        break_on_hyphens=False,
    )
    fig.text(
        x + width / 2,
        y + height * 0.70,
        card_name,
        fontsize=7.5,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="center",
        va="center",
    )
    fig.text(
        x + width / 2,
        y + height * 0.22,
        f"{row['Average_Copies']:.2f} | {row['Inclusion']:.2f}%",
        fontsize=8.5,
        fontweight="bold",
        color=tier_color,
        ha="center",
        va="center",
    )


def create_chart(report, tournament_name, group_name, total_decks):
    """Create the complete tiered card grid."""
    tier_count = report["tier_index"].nunique() if not report.empty else 0
    layout_rows = 0
    for tier_index in report["tier_index"].unique():
        tier_df = report[report["tier_index"] == tier_index]
        layout_rows += 1
        for _, type_df in tier_df.groupby("card_type", sort=False):
            layout_rows += 1 + max(1, (len(type_df) + 7) // 8)

    figure_height = max(9.0, 3.7 + layout_rows * 0.78)
    fig = plt.figure(figsize=(16, figure_height), dpi=300)
    fig.patch.set_facecolor("#F4F4F4")
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.text(
        0.06, 0.965, "Core Cards", fontsize=25, fontweight="bold",
        color=TEXT_COLOR, ha="left", va="top",
    )
    fig.text(
        0.06, 0.928,
        f"{tournament_name}  •  {group_name}  •  {total_decks} Masters decklists",
        fontsize=13, color=SECONDARY_TEXT_COLOR, ha="left", va="top",
    )
    fig.text(
        0.94, 0.965, "PTCG Data Viz", fontsize=18, fontweight="bold",
        color=BRAND_DARK, ha="right", va="top",
    )

    left, right = 0.06, 0.94
    columns = 8
    gap = 0.012
    tile_width = (right - left - gap * (columns - 1)) / columns
    row_step = 0.79 / max(layout_rows, 1)
    tile_height = row_step * 0.78
    row_gap = row_step * 0.12
    section_gap = row_step * 0.10
    y = 0.87
    divider_lines = []

    for tier_index, (tier_label, _, _, tier_color) in enumerate(TIER_DEFINITIONS):
        tier_df = report[report["tier_index"] == tier_index]
        if tier_df.empty:
            continue

        fig.text(
            left,
            y,
            tier_label,
            fontsize=11,
            fontweight="bold",
            color=tier_color,
            ha="left",
            va="center",
        )
        divider_lines.append((left + 0.10, y, right, y, tier_color))
        y -= row_step

        for card_type, type_df in tier_df.groupby("card_type", sort=False):
            fig.text(
                left,
                y,
                _section_name(card_type),
                fontsize=8.5,
                fontweight="bold",
                color=SECTION_COLORS.get(card_type, SECONDARY_TEXT_COLOR),
                ha="left",
                va="center",
            )
            y -= row_step
            column = 0

            for _, row in type_df.iterrows():
                x = left + column * (tile_width + gap)
                _draw_tile(fig, row, x, y, tile_width, tile_height, tier_color)

                column += 1
                if column == columns:
                    column = 0
                    y -= row_step

            if column:
                y -= row_step

        y -= section_gap

    fig.text(
        left,
        0.018,
        "Average copies are calculated among decks containing the card. Inclusion is the share of selected Masters decklists containing the card.",
        fontsize=9,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
    )
    fig._core_divider_lines = divider_lines
    return fig


def add_core_overlays(output_path, fig):
    """Add tile outlines and tier dividers with Pillow after export."""
    from PIL import Image, ImageDraw

    image = Image.open(output_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    def point(x, y):
        return int(x * width), int((1 - y) * height)

    for x, y, tile_width, tile_height in getattr(fig, "_core_tile_boxes", []):
        draw.rounded_rectangle(
            [
                point(x, y + tile_height),
                point(x + tile_width, y),
            ],
            radius=max(3, int(width / 500)),
            outline=BORDER_COLOR,
            width=max(1, int(width / 1800)),
        )

    for x1, y1, x2, y2, color in getattr(fig, "_core_divider_lines", []):
        draw.line(
            [point(x1, y1), point(x2, y2)],
            fill=color,
            width=max(2, int(width / 700)),
        )

    image.save(output_path)


def main():
    tournament_id, tournament_name = select_tournament()
    cards = get_archetype_cards(tournament_id)
    grouping = select_grouping()
    archetype = select_archetype(cards)
    cards = cards[cards["overall"] == archetype].copy()

    variant = None
    if grouping == "variant":
        variant = select_variant(cards)
        cards = cards[cards["variant"] == variant].copy()

    report = build_report(cards)
    if report.empty:
        print("No card data found for the selected deck group.")
        return

    total_decks = cards["player_key"].nunique()
    group_name = _display_group_name(archetype, variant)
    print(f"\n{group_name}: {len(report)} cards across {total_decks} Masters decklists")
    print(report[["card_name", "card_type", "Average_Copies", "Inclusion"]].to_string(index=False))

    fig = create_chart(report, tournament_name, group_name, total_decks)
    output_path = save_chart(
        fig,
        "core_cards.png",
        output_directory=OUTPUT_DIRECTORY,
        bbox_inches=None,
        facecolor="#F4F4F4",
        opaque_background=True,
    )
    add_core_overlays(output_path, fig)
    plt.close(fig)
    print(f"\nChart saved to:\n{output_path}")


if __name__ == "__main__":
    main()
