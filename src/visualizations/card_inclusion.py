"""
Card inclusion visualization.

Shows how frequently cards appear in the selected archetype or variant's
decks for one tournament. The inclusion percentage is calculated across
selected decks, while average copies is calculated among decks containing
the card.
"""

import math
import textwrap
from pathlib import Path

import pandas as pd

from src.analytics_queries import (
    get_archetype_cards,
    get_tournaments,
)

from src.visualizations.chart_style import (
    BRAND_COLOR,
    BACKGROUND_COLOR,
    SECONDARY_TEXT_COLOR,
    TEXT_COLOR,
    add_footer,
    save_chart,
    setup_chart,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "src"
    / "visualizations"
    / "output"
    / "visualizations"
)


def select_tournament():
    """Display available tournaments and return the selected tournament."""
    tournaments = get_tournaments()

    print("\nAvailable Tournaments:\n")

    for index, row in tournaments.iterrows():
        print(f"{index + 1}. {row['tournament_name']}")

    while True:
        try:
            selection = int(input("\nSelect tournament: "))

            if 1 <= selection <= len(tournaments):
                break

            print(
                f"Please enter a number between 1 and {len(tournaments)}."
            )

        except ValueError:
            print("Please enter a valid number.")

    tournament = tournaments.iloc[selection - 1]

    return tournament["tournament_id"], tournament["tournament_name"]


def select_grouping():
    """Prompt for overall archetype or variant selection."""
    print("\nSelect deck grouping:\n")
    print("1. Overall Archetype")
    print("2. Variant")

    while True:
        try:
            selection = int(input("\nSelect grouping: "))

            if selection == 1:
                return "overall"

            if selection == 2:
                return "variant"

            print("Please enter 1 or 2.")

        except ValueError:
            print("Please enter a valid number.")


def select_archetype(df):
    """Prompt for an archetype from the selected tournament."""
    archetypes = sorted(df["overall"].dropna().unique())

    print("\nAvailable Archetypes:\n")

    for index, archetype in enumerate(archetypes, start=1):
        print(f"{index}. {archetype}")

    while True:
        try:
            selection = int(input("\nSelect archetype: "))

            if 1 <= selection <= len(archetypes):
                return archetypes[selection - 1]

            print(
                f"Please enter a number between 1 and {len(archetypes)}."
            )

        except ValueError:
            print("Please enter a valid number.")


def select_variant(df):
    """Prompt for a variant, including the overall archetype option."""
    variants = sorted(df["variant"].dropna().unique())

    print("\nAvailable Variants:\n")
    print("1. Overall")

    for index, variant in enumerate(variants, start=2):
        print(f"{index}. {variant}")

    while True:
        try:
            selection = int(input("\nSelect variant: "))

            if selection == 1:
                return None

            if 2 <= selection <= len(variants) + 1:
                return variants[selection - 2]

            print(
                f"Please enter a number between 1 and {len(variants) + 1}."
            )

        except ValueError:
            print("Please enter a valid number.")


def build_card_inclusion_report(df):
    """Build the established card inclusion report for selected decks."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "card_name",
                "card_type",
                "Decks",
                "Inclusion",
                "Average_Copies",
            ]
        )

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

    return report.sort_values(
        ["Inclusion", "Average_Copies", "card_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


CARD_TYPE_STYLES = {
    "pokemon": ("#EAF3E6", "#5D8A4D"),
    "trainer": ("#E8EEF8", "#4A6FA5"),
    "energy": ("#F6EBD7", "#B27B25"),
}


def _card_type_order(card_type):
    """Keep the reference layout ordered as Pokémon, Trainer, Energy."""
    key = str(card_type).strip().lower()

    for index, name in enumerate(("pokemon", "trainer", "energy")):
        if name in key:
            return index

    return 99


def _draw_card_tile(fig, row, x, y, width, height):
    """Draw one image-free card tile in axes coordinates."""
    if not hasattr(fig, "_card_tile_boxes"):
        fig._card_tile_boxes = []

    fig._card_tile_boxes.append((x, y, width, height))

    short_name = textwrap.shorten(
        str(row["card_name"]),
        width=28,
        placeholder="…",
    )
    card_name = textwrap.fill(
        short_name,
        width=16,
        break_long_words=False,
        break_on_hyphens=False,
    )
    fig.text(
        x + width / 2,
        y + height * 0.78,
        card_name,
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
        color=TEXT_COLOR,
        linespacing=0.9,
        multialignment="center",
    )

    fig.text(
        x + width / 2,
        y + height * 0.20,
        f"{row['Average_Copies']:.2f} | {row['Inclusion']:.0f}%",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=BRAND_COLOR,
    )


def create_chart(report, tournament_name, group_name, total_decks, number_of_cards):
    """Create a sectioned card-grid visualization without card artwork."""
    chart_data = report.head(number_of_cards).copy()
    chart_data["_type_order"] = chart_data["card_type"].map(_card_type_order)
    chart_data = chart_data.sort_values(
        ["_type_order", "Inclusion", "Average_Copies", "card_name"],
        ascending=[True, False, False, True],
    )

    sections = [
        ("Pokémon", "pokemon"),
        ("Trainer", "trainer"),
        ("Energy", "energy"),
    ]
    section_data = []

    for section_name, section_key in sections:
        matching = chart_data[
            chart_data["card_type"].apply(
                lambda value: section_key in str(value).lower()
            )
        ].copy()

        if not matching.empty:
            section_data.append((section_name, section_key, matching))

    known_card_types = chart_data["card_type"].apply(
        lambda value: any(
            section_key in str(value).lower()
            for _, section_key in sections
        )
    )
    other_cards = chart_data[~known_card_types].copy()

    if not other_cards.empty:
        section_data.append(("Other", "other", other_cards))

    fig, ax = setup_chart(
        title="Card Inclusion",
        subtitle=(
            f"{tournament_name}  •  {group_name}  •  "
            f"{total_decks} Masters decklists"
        ),
    )

    fig.patch.set_facecolor("#F4F4F4")
    fig.patch.set_visible(False)
    ax.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    columns = 8 if len(chart_data) >= 16 else 6 if len(chart_data) >= 9 else 4
    total_rows = sum(
        math.ceil(len(section) / columns)
        for _, _, section in section_data
    )
    section_count = len(section_data)
    left = 0.045
    right = 0.955
    top = 0.82
    bottom = 0.12
    horizontal_gap = 0.012
    vertical_gap = 0.022
    section_gap = 0.030
    section_header_height = 0.025
    tile_width = (right - left - horizontal_gap * (columns - 1)) / columns
    tile_height = min(
        0.22,
        (
            top
            - bottom
            - vertical_gap * (total_rows - section_count)
            - section_gap * (section_count - 1)
            - section_header_height * section_count
        )
        / total_rows,
    )

    fig.set_size_inches(
        16,
        max(9, 3.5 + total_rows * 0.9),
    )

    current_y = top

    fig._card_section_lines = []

    for section_index, (section_name, section_key, section) in enumerate(
        section_data
    ):
        _, accent_color = CARD_TYPE_STYLES.get(
            section_key,
            ("#EEEEEE", SECONDARY_TEXT_COLOR),
        )

        fig.text(
            left,
            current_y,
            section_name,
            ha="left",
            va="top",
            fontsize=11,
            fontweight="bold",
            color=accent_color,
        )

        fig._card_section_lines.append(
            (left + 0.085, right, current_y - 0.008, accent_color)
        )

        current_y -= section_header_height
        section_rows = math.ceil(len(section) / columns)

        for index, (_, row) in enumerate(section.iterrows()):
            column = index % columns
            row_index = index // columns
            x = left + column * (tile_width + horizontal_gap)
            y = (
                current_y
                - (row_index + 1) * tile_height
                - row_index * vertical_gap
            )
            _draw_card_tile(fig, row, x, y, tile_width, tile_height)

        current_y -= (
            section_rows * tile_height
            + (section_rows - 1) * vertical_gap
        )

        if section_index < section_count - 1:
            current_y -= section_gap

    add_footer(fig)

    return fig


def add_card_grid_overlays(output_path, fig):
    """Add tile outlines and section dividers after Matplotlib export."""
    from PIL import Image, ImageColor, ImageDraw

    image = Image.open(output_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    image_width, image_height = image.size

    for x, y, width, height in getattr(fig, "_card_tile_boxes", []):
        left = round(x * image_width)
        top = round((1 - y - height) * image_height)
        right = round((x + width) * image_width)
        bottom = round((1 - y) * image_height)

        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=10,
            outline="#CFCFCF",
            width=2,
        )

    for x_start, x_end, y, color in getattr(fig, "_card_section_lines", []):
        draw.line(
            (
                round(x_start * image_width),
                round((1 - y) * image_height),
                round(x_end * image_width),
                round((1 - y) * image_height),
            ),
            fill=ImageColor.getrgb(color),
            width=3,
        )

    image.save(output_path)


def main():
    """Run the interactive card inclusion visualization."""
    tournament_id, tournament_name = select_tournament()
    df = get_archetype_cards(tournament_id)

    if df.empty:
        print("\nNo classified card data found for this tournament.")
        return

    grouping = select_grouping()
    archetype = select_archetype(df)

    selected = df[df["overall"] == archetype].copy()
    group_name = archetype

    if grouping == "variant":
        variant = select_variant(selected)

        if variant is not None:
            selected = selected[selected["variant"] == variant].copy()
            group_name = (
                archetype
                if variant == "Default"
                else f"{archetype} — {variant}"
            )

    if selected["player_key"].nunique() == 0:
        print("\nNo decks found for the selected group.")
        return

    report = build_card_inclusion_report(selected)
    number_of_cards = len(report)
    total_decks = selected["player_key"].nunique()

    print()
    print("=" * 60)
    print(tournament_name)
    print(group_name)
    print("=" * 60)
    print()
    print(report.head(number_of_cards)[
        ["card_name", "card_type", "Decks", "Inclusion", "Average_Copies"]
    ].to_string(
        index=False,
        formatters={
            "Inclusion": "{:.1f}%".format,
            "Average_Copies": "{:.1f}".format,
        },
    ))

    fig = create_chart(
        report,
        tournament_name,
        group_name,
        total_decks,
        number_of_cards,
    )

    output_path = save_chart(
        fig,
        "card_inclusion.png",
        output_directory=OUTPUT_DIRECTORY,
        bbox_inches=None,
        facecolor="#F4F4F4",
        opaque_background=True,
    )
    add_card_grid_overlays(output_path, fig)
    print(f"\nChart saved to:\n{output_path}")


if __name__ == "__main__":
    main()
