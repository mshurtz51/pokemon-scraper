"""
Card inclusion timeline visualization by tournament.

Shows every card used by a selected archetype or variant across the selected
Masters tournaments. The table is intentionally complete rather than Top-N
limited so the output can show the full card pool for the selected deck.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analytics_queries import (
    get_archetype_cards,
    get_tournaments,
)
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


SECTION_COLORS = {
    "pokemon": "#5A8F4D",
    "trainer": "#4F73A8",
    "energy": "#B47A17",
    "other": SECONDARY_TEXT_COLOR,
}


def select_tournaments():
    """Prompt for one or more tournaments."""
    tournaments = get_tournaments()

    print()
    print("=" * 60)
    print("TOURNAMENTS")
    print("=" * 60)

    for index, row in tournaments.iterrows():
        print(f"{index + 1}. {row['tournament_name']}")

    choices = input("\nSelect tournaments (comma separated): ")
    indices = [int(value.strip()) - 1 for value in choices.split(",")]
    selected = tournaments.iloc[indices].copy()

    return selected.sort_values("start_date")


def select_archetype(cards):
    """Prompt for an archetype represented in the selected tournaments."""
    archetypes = sorted(cards["overall"].dropna().unique())

    print()
    print("=" * 60)
    print("ARCHETYPES")
    print("=" * 60)

    for index, archetype in enumerate(archetypes, start=1):
        print(f"{index}. {archetype}")

    choice = int(input("\nSelect archetype: "))
    return archetypes[choice - 1]


def select_variant(cards, archetype):
    """Prompt for overall archetype or one of its variants."""
    variants = sorted(
        cards.loc[cards["overall"] == archetype, "variant"]
        .dropna()
        .unique()
    )

    print()
    print("=" * 60)
    print("VARIANTS")
    print("=" * 60)
    print("1. Overall")

    for index, variant in enumerate(variants, start=2):
        print(f"{index}. {variant}")

    choice = int(input("\nSelect variant: "))

    if choice == 1:
        return None

    return variants[choice - 2]


def load_selected_cards(tournaments):
    """Load card rows for the selected tournaments."""
    frames = []

    for _, tournament in tournaments.iterrows():
        cards = get_archetype_cards(tournament["tournament_id"]).copy()
        cards["tournament_name"] = tournament["tournament_name"]
        frames.append(cards)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def build_report(cards, tournaments, archetype, variant=None):
    """Build card inclusion percentages for the selected deck group."""
    filtered = cards[cards["overall"] == archetype].copy()

    if variant is not None:
        filtered = filtered[filtered["variant"] == variant].copy()

    if filtered.empty:
        return pd.DataFrame(), {}

    deck_counts = (
        filtered.groupby("tournament_name")["player_key"]
        .nunique()
        .to_dict()
    )

    rows = []

    for (card_name, card_type), card_df in filtered.groupby(
        ["card_name", "card_type"],
        dropna=False,
    ):
        row = {
            "card_name": card_name,
            "card_type": card_type if pd.notna(card_type) else "other",
        }

        for tournament in tournaments["tournament_name"]:
            tournament_cards = card_df[
                card_df["tournament_name"] == tournament
            ]
            total_decks = deck_counts.get(tournament, 0)
            decks = tournament_cards["player_key"].nunique()
            row[tournament] = (
                decks / total_decks * 100
                if total_decks
                else 0.0
            )

        rows.append(row)

    report = pd.DataFrame(rows)
    tournament_names = tournaments["tournament_name"].tolist()
    report["_latest"] = report[tournament_names[-1]]
    report["_average"] = report[tournament_names].mean(axis=1)
    report["_type_order"] = report["card_type"].map(
        {"pokemon": 0, "trainer": 1, "energy": 2}
    ).fillna(3)
    report = report.sort_values(
        ["_type_order", "_latest", "_average", "card_name"],
        ascending=[True, False, False, True],
    ).drop(columns=["_latest", "_average", "_type_order"])

    return report.reset_index(drop=True), deck_counts


def _display_group_name(archetype, variant):
    if variant is None or variant == "Default":
        return archetype
    return f"{archetype} — {variant}"


def _value_color(value):
    if value >= 80:
        return "#2F7D4A"
    if value >= 40:
        return "#9A7015"
    if value > 0:
        return BRAND_COLOR
    return "#A0A0A0"


def _section_name(card_type):
    return {
        "pokemon": "Pokémon",
        "trainer": "Trainer",
        "energy": "Energy",
    }.get(card_type, "Other")


def create_chart(report, tournaments, group_name, deck_counts):
    """Create the complete timeline table without Matplotlib patches."""
    tournament_names = tournaments["tournament_name"].tolist()
    row_count = len(report)
    section_count = report["card_type"].nunique()

    # Keep every card visible while preserving legible row spacing.
    figure_height = max(9.0, 3.8 + (row_count + section_count) * 0.34)
    fig = plt.figure(figsize=(16, figure_height), dpi=300)
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.text(
        0.06,
        0.965,
        "Card Inclusion Timeline",
        fontsize=25,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="left",
        va="top",
    )
    fig.text(
        0.06,
        0.928,
        f"{group_name}  •  {len(tournament_names)} tournaments",
        fontsize=13,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="top",
    )
    fig.text(
        0.94,
        0.965,
        "PTCG Data Viz",
        fontsize=18,
        fontweight="bold",
        color=BRAND_DARK,
        ha="right",
        va="top",
    )

    left = 0.06
    right = 0.94
    table_top = 0.875
    table_bottom = 0.055
    table_width = right - left
    name_width = 0.28
    column_width = (table_width - name_width) / max(len(tournament_names), 1)
    row_height = (table_top - table_bottom) / max(
        row_count + section_count + 1,
        1,
    )

    fig.text(
        left + name_width / 2,
        table_top,
        "Card",
        fontsize=10,
        fontweight="bold",
        color=BRAND_DARK,
        ha="center",
        va="center",
    )

    for index, tournament in enumerate(tournaments.itertuples()):
        x = left + name_width + index * column_width + column_width / 2
        fig.text(
            x,
            table_top,
            tournament.tournament_name,
            fontsize=9,
            fontweight="bold",
            color=BRAND_DARK,
            ha="center",
            va="center",
        )

    tile_boxes = []
    divider_lines = []
    row_y = table_top - row_height
    previous_type = None

    for _, row in report.iterrows():
        card_type = row["card_type"]

        if card_type != previous_type:
            section_y = row_y + row_height * 0.5
            divider_lines.append(
                (left, section_y, right, section_y, SECTION_COLORS.get(card_type, SECONDARY_TEXT_COLOR))
            )
            fig.text(
                left,
                row_y + row_height * 0.62,
                _section_name(card_type),
                fontsize=10,
                fontweight="bold",
                color=SECTION_COLORS.get(card_type, SECONDARY_TEXT_COLOR),
                ha="left",
                va="center",
            )
            row_y -= row_height
            previous_type = card_type

        fig.text(
            left + name_width / 2,
            row_y + row_height * 0.55,
            str(row["card_name"]),
            fontsize=9,
            color=TEXT_COLOR,
            ha="center",
            va="center",
        )

        for index, tournament in enumerate(tournament_names):
            value = float(row[tournament])
            x = left + name_width + index * column_width
            center = x + column_width / 2
            fig.text(
                center,
                row_y + row_height * 0.55,
                f"{value:.2f}%" if value else "—",
                fontsize=10,
                fontweight="bold",
                color=_value_color(value),
                ha="center",
                va="center",
            )

        tile_boxes.append((left, row_y, right, row_y + row_height))
        row_y -= row_height

    fig.text(
        left,
        0.018,
        "Percentages show the share of Masters decklists for the selected archetype containing each card.",
        fontsize=9,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
    )

    fig._timeline_tile_boxes = tile_boxes
    fig._timeline_divider_lines = divider_lines
    fig._timeline_deck_counts = deck_counts
    return fig


def add_timeline_overlays(output_path, fig):
    """Add tile outlines and section dividers with Pillow after export."""
    from PIL import Image, ImageDraw

    image = Image.open(output_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    def point(x, y):
        return int(x * width), int((1 - y) * height)

    for left, bottom, right, top in getattr(fig, "_timeline_tile_boxes", []):
        draw.line(
            [point(left, bottom), point(right, bottom)],
            fill=BORDER_COLOR,
            width=max(1, int(width / 1800)),
        )

    for left, y1, right, y2, color in getattr(fig, "_timeline_divider_lines", []):
        draw.line(
            [point(left, y1), point(right, y2)],
            fill=color,
            width=max(2, int(width / 700)),
        )

    image.save(output_path)


def main():
    tournaments = select_tournaments()
    if tournaments.empty:
        print("No tournaments selected.")
        return

    cards = load_selected_cards(tournaments)
    if cards.empty:
        print("No card data found for the selected tournaments.")
        return

    archetype = select_archetype(cards)
    variant = select_variant(cards, archetype)
    report, deck_counts = build_report(
        cards,
        tournaments,
        archetype,
        variant,
    )

    if report.empty:
        print("No cards found for the selected deck group.")
        return

    group_name = _display_group_name(archetype, variant)
    print()
    print(f"{group_name}: {len(report)} cards across {len(tournaments)} tournaments")
    print()
    print(report.to_string(index=False))

    fig = create_chart(report, tournaments, group_name, deck_counts)
    output_path = save_chart(
        fig,
        "card_inclusion_timeline.png",
        output_directory=OUTPUT_DIRECTORY,
        bbox_inches=None,
        facecolor=BACKGROUND_COLOR,
        opaque_background=True,
    )
    add_timeline_overlays(output_path, fig)
    plt.close(fig)
    print(f"\nChart saved to:\n{output_path}")


if __name__ == "__main__":
    main()
