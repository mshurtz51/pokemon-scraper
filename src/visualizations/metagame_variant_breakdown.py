"""
Metagame variant breakdown visualization.

Drills into one archetype and compares its variants by composition and finish
performance. This is intentionally narrower than the full-field Meta Share
visualization.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analytics_queries import get_archetype_summary, get_tournaments
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


def select_archetype(results):
    """Prompt for one archetype."""
    archetypes = sorted(results["overall"].dropna().unique())

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


def build_report(results, archetype):
    """Build variant composition and finish metrics."""
    filtered = results[results["overall"] == archetype].copy()
    if filtered.empty:
        return pd.DataFrame()

    filtered["variant_label"] = filtered["variant"].fillna("Default")
    filtered.loc[filtered["variant_label"] == "Default", "variant_label"] = archetype
    total_decks = len(filtered)

    report = (
        filtered.groupby("variant_label")
        .agg(
            Decklists=("player_key", "nunique"),
            Average_Finish=("standing", "mean"),
            Median_Finish=("standing", "median"),
            Best_Finish=("standing", "min"),
        )
        .reset_index()
        .rename(columns={"variant_label": "Variant"})
    )
    report["Archetype_Share"] = report["Decklists"] / total_decks * 100
    report = report.sort_values(
        ["Decklists", "Average_Finish", "Variant"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    return report


def _finish_color(value, minimum, maximum):
    if maximum == minimum:
        return "#8A741C"
    ratio = (value - minimum) / (maximum - minimum)
    if ratio <= 0.35:
        return "#2F7D4A"
    if ratio >= 0.7:
        return BRAND_COLOR
    return "#8A741C"


def create_chart(report, tournament_name, archetype, total_decks):
    """Create the archetype variant breakdown table."""
    row_count = len(report)
    figure_height = max(9.0, 6.4 + row_count * 0.42)
    fig = plt.figure(figsize=(16, figure_height), dpi=300)
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.text(
        0.06, 0.965, "Metagame Variant Breakdown", fontsize=25,
        fontweight="bold", color=TEXT_COLOR, ha="left", va="top",
    )
    fig.text(
        0.06, 0.928,
        f"{tournament_name}  •  {archetype}  •  {total_decks} Masters decklists",
        fontsize=13, color=SECONDARY_TEXT_COLOR, ha="left", va="top",
    )
    fig.text(
        0.94, 0.965, "PTCG Data Viz", fontsize=18,
        fontweight="bold", color=BRAND_DARK, ha="right", va="top",
    )

    fig.text(
        0.06, 0.865, "Variant composition and finish performance",
        fontsize=11, fontweight="bold", color=BRAND_DARK,
        ha="left", va="center",
    )
    fig.text(
        0.06, 0.832,
        "Share is within the selected archetype; lower finish numbers indicate better finishes.",
        fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="center",
    )

    left, right = 0.06, 0.94
    top, bottom = 0.77, 0.17
    table_width = right - left
    row_height = (top - bottom) / max(row_count + 1, 1)
    widths = [0.28, 0.14, 0.16, 0.14, 0.14, 0.14]
    headers = [
        "Variant", "Decklists", "Archetype Share",
        "Average Finish", "Median Finish", "Best Finish",
    ]
    x_positions = [left]
    for width in widths[:-1]:
        x_positions.append(x_positions[-1] + table_width * width)

    fig._breakdown_lines = []
    fig._breakdown_header = (left, top - row_height, right, top, BRAND_DARK)
    header_y = top - row_height / 2

    for index, header in enumerate(headers):
        x = x_positions[index]
        width = table_width * widths[index]
        fig.text(
            x + width / 2, header_y, header, fontsize=9,
            fontweight="bold", color=BRAND_DARK,
            ha="center", va="center",
        )

    finish_values = pd.concat(
        [report["Average_Finish"], report["Median_Finish"], report["Best_Finish"]]
    )
    finish_min = finish_values.min()
    finish_max = finish_values.max()

    for row_index, (_, row) in enumerate(report.iterrows()):
        y = top - (row_index + 1.5) * row_height
        values = [
            row["Variant"],
            f"{int(row['Decklists'])}",
            f"{row['Archetype_Share']:.2f}%",
            f"{row['Average_Finish']:.1f}",
            f"{row['Median_Finish']:.1f}",
            f"{int(row['Best_Finish'])}",
        ]
        colors = [
            TEXT_COLOR,
            TEXT_COLOR,
            BRAND_COLOR,
            _finish_color(row["Average_Finish"], finish_min, finish_max),
            _finish_color(row["Median_Finish"], finish_min, finish_max),
            _finish_color(row["Best_Finish"], finish_min, finish_max),
        ]

        for index, value in enumerate(values):
            x = x_positions[index]
            width = table_width * widths[index]
            fig.text(
                x + width / 2, y, str(value), fontsize=10,
                fontweight="bold" if index >= 2 else "normal",
                color=colors[index], ha="center", va="center",
            )
        fig._breakdown_lines.append((left, y - row_height / 2, right, y - row_height / 2))

    fig.text(
        left, 0.11,
        "Average and median finish are calculated among Masters players using the selected archetype variant.",
        fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom",
    )
    fig.text(
        left, 0.075,
        "Green = stronger finishes  •  Yellow = middle of this archetype  •  Red = weaker finishes",
        fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom",
    )
    return fig


def add_breakdown_overlays(output_path, fig):
    """Add table rules with Pillow after export."""
    from PIL import Image, ImageDraw

    image = Image.open(output_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    def point(x, y):
        return int(x * width), int((1 - y) * height)

    left, bottom, right, top, color = fig._breakdown_header
    for y in (bottom, top):
        draw.line(
            [point(left, y), point(right, y)],
            fill=color,
            width=max(2, int(width / 700)),
        )

    for x1, y1, x2, y2 in fig._breakdown_lines:
        draw.line(
            [point(x1, y1), point(x2, y2)],
            fill=BORDER_COLOR,
            width=max(1, int(width / 1800)),
        )

    image.save(output_path)


def main():
    tournament_id, tournament_name = select_tournament()
    results = get_archetype_summary(tournament_id)
    if results.empty:
        print("No tournament results found.")
        return

    archetype = select_archetype(results)
    report = build_report(results, archetype)
    total_decks = int(report["Decklists"].sum())

    print()
    print(report.to_string(index=False))

    fig = create_chart(report, tournament_name, archetype, total_decks)
    output_path = save_chart(
        fig,
        "metagame_variant_breakdown.png",
        output_directory=OUTPUT_DIRECTORY,
        bbox_inches=None,
        facecolor=BACKGROUND_COLOR,
        opaque_background=True,
    )
    add_breakdown_overlays(output_path, fig)
    plt.close(fig)
    print(f"\nChart saved to:\n{output_path}")


if __name__ == "__main__":
    main()
