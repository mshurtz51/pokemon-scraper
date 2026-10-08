"""
Cumulative conversion visualization.

Shows how each archetype converts tournament representation into cumulative
top-cut finishes. All calculations use classified Masters results.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analytics_queries import get_tournament_results, get_tournaments
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

CUTS = [8, 16, 32, 64, 128, 256, 512]


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


def select_display_count(max_count):
    """Prompt for the number of groups to display."""
    print("\nHow many groups should be displayed?\n")
    print("0. All groups")

    while True:
        try:
            choice = int(input(f"\nSelect 0-{max_count}: "))
            if 0 <= choice <= max_count:
                return None if choice == 0 else choice
        except ValueError:
            pass
        print(f"Please enter a whole number from 0 to {max_count}.")


def select_grouping():
    """Prompt for archetype-level or variant-level conversion."""
    print("\nShow cumulative conversion by:\n")
    print("1. Archetype")
    print("2. Variant")

    while True:
        try:
            choice = int(input("\nSelect grouping: "))
            if choice == 1:
                return "archetype"
            if choice == 2:
                return "variant"
        except ValueError:
            pass
        print("Please enter 1 or 2.")


def build_report(results, cuts=CUTS, grouping="archetype"):
    """Build cumulative top-cut counts and Performance Index values."""
    if results.empty:
        return pd.DataFrame()

    results = results.copy()
    results["standing"] = pd.to_numeric(results["standing"], errors="coerce")
    results = results.dropna(subset=["overall", "standing"])
    total_players = len(results)

    if grouping == "variant":
        results["Group"] = results.apply(
            lambda row: (
                row["overall"]
                if row["variant"] in (None, "", "Default")
                else f"{row['overall']} — {row['variant']}"
            ),
            axis=1,
        )
    else:
        results["Group"] = results["overall"]

    summary = (
        results.groupby("Group")
        .size()
        .reset_index(name="Players")
        .rename(columns={"Group": "Group"})
    )
    summary["Meta Share"] = summary["Players"] / total_players * 100

    for cut in cuts:
        counts = (
            results[results["standing"] <= cut]
            .groupby("Group")
            .size()
            .reindex(summary["Group"], fill_value=0)
            .to_numpy()
        )
        column = f"Top {cut}"
        summary[column] = counts.astype(int)
        expected_share = summary["Players"] / total_players
        top_share = summary[column] / cut
        summary[f"PI {column}"] = top_share / expected_share

    summary["Sort Top 64"] = summary["Top 64"]
    summary["Sort Top 128"] = summary["Top 128"]
    summary = summary.sort_values(
        ["Sort Top 64", "Sort Top 128", "Meta Share", "Group"],
        ascending=[False, False, False, True],
    )
    return summary.drop(columns=["Sort Top 64", "Sort Top 128"]).reset_index(drop=True)


def _pi_color(value):
    if value >= 1.15:
        return "#2F7D4A"
    if value <= 0.85:
        return BRAND_COLOR
    return "#8A741C"


def _format_cell(count, pi):
    if not count:
        return "—"
    return f"{int(count)}  |  {pi:.2f}x"


def create_chart(report, tournament_name, grouping):
    """Create the cumulative conversion table."""
    row_count = len(report)
    figure_height = max(9.0, 4.4 + row_count * 0.31)
    fig = plt.figure(figsize=(16, figure_height), dpi=300)
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.text(
        0.05, 0.965, "Cumulative Conversion", fontsize=25,
        fontweight="bold", color=TEXT_COLOR, ha="left", va="top",
    )
    fig.text(
        0.05, 0.928,
        f"{tournament_name}  •  {grouping} view  •  Masters results  •  cumulative top-cut finishes",
        fontsize=13, color=SECONDARY_TEXT_COLOR, ha="left", va="top",
    )
    fig.text(
        0.95, 0.965, "PTCG Data Viz", fontsize=18,
        fontweight="bold", color=BRAND_DARK, ha="right", va="top",
    )

    left, right = 0.05, 0.95
    top, bottom = 0.87, 0.145
    table_width = right - left
    row_height = (top - bottom) / max(row_count + 1, 1)
    widths = [0.25, 0.08, 0.10] + [0.57 / len(CUTS)] * len(CUTS)
    group_header = "Archetype" if grouping == "Archetype" else "Archetype / Variant"
    headers = [group_header, "Players", "Meta Share"] + [f"Top {cut}" for cut in CUTS]

    x_positions = [left]
    for width in widths[:-1]:
        x_positions.append(x_positions[-1] + table_width * width)

    fig._conversion_lines = []
    header_y = top - row_height / 2
    for index, header in enumerate(headers):
        x = x_positions[index]
        width = table_width * widths[index]
        fig.text(
            x + width / 2,
            header_y,
            header,
            fontsize=9,
            fontweight="bold",
            color=BRAND_DARK,
            ha="center",
            va="center",
        )

    # Header and table separators are drawn with Pillow after export because
    # this environment can crash when Matplotlib patches are rendered.
    fig._conversion_header = (left, top - row_height, right, top, BRAND_DARK)

    for row_index, (_, row) in enumerate(report.iterrows()):
        y = top - (row_index + 1.5) * row_height
        values = [
            row["Group"],
            f"{int(row['Players'])}",
            f"{row['Meta Share']:.2f}%",
        ]
        colors = [TEXT_COLOR, TEXT_COLOR, TEXT_COLOR]

        for cut in CUTS:
            values.append(_format_cell(row[f"Top {cut}"], row[f"PI Top {cut}"]))
            colors.append(_pi_color(row[f"PI Top {cut}"]))

        for index, value in enumerate(values):
            x = x_positions[index]
            width = table_width * widths[index]
            fig.text(
                x + width / 2,
                y,
                str(value),
                fontsize=8.5,
                fontweight="bold" if index >= 3 else "normal",
                color=colors[index],
                ha="center",
                va="center",
            )

        fig._conversion_lines.append((left, y - row_height / 2, right, y - row_height / 2))

    fig.text(
        left,
        0.095,
        "Each cell shows cumulative finishes through the cut, followed by Performance Index.",
        fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom",
    )
    fig.text(
        left,
        0.065,
        "1.00x = expected representation  •  >1.00x = overrepresented  •  <1.00x = underrepresented",
        fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom",
    )
    fig.text(
        left,
        0.035,
        "Cumulative counts include every finish at or above each cut; PI compares top-cut share with expected share from meta share.",
        fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom",
    )
    return fig


def add_conversion_overlays(output_path, fig):
    """Add the table header and row separators with Pillow."""
    from PIL import Image, ImageDraw

    image = Image.open(output_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    def point(x, y):
        return int(x * width), int((1 - y) * height)

    left, bottom, right, top, color = fig._conversion_header
    draw.line(
        [point(left, bottom), point(right, bottom)],
        fill=color,
        width=max(2, int(width / 700)),
    )
    draw.line(
        [point(left, top), point(right, top)],
        fill=color,
        width=max(2, int(width / 700)),
    )

    for x1, y1, x2, y2 in fig._conversion_lines:
        draw.line(
            [point(x1, y1), point(x2, y2)],
            fill=BORDER_COLOR,
            width=max(1, int(width / 1800)),
        )

    image.save(output_path)


def main():
    tournament_id, tournament_name = select_tournament()
    results = get_tournament_results(tournament_id)
    grouping = select_grouping()
    grouping_label = "Archetype" if grouping == "archetype" else "Variant"
    report = build_report(results, grouping=grouping)

    if report.empty:
        print("No tournament results found.")
        return

    display_count = select_display_count(len(report))
    if display_count is not None:
        report = report.head(display_count).copy()

    print()
    print(report.to_string(index=False))

    fig = create_chart(report, tournament_name, grouping_label)
    output_path = save_chart(
        fig,
        "cumulative_conversion.png",
        output_directory=OUTPUT_DIRECTORY,
        bbox_inches=None,
        facecolor=BACKGROUND_COLOR,
        opaque_background=True,
    )
    add_conversion_overlays(output_path, fig)
    plt.close(fig)
    print(f"\nChart saved to:\n{output_path}")


if __name__ == "__main__":
    main()
