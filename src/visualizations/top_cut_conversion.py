"""
Top Cut Conversion visualization.

Shows how archetypes or variants convert tournament representation into
cumulative Top 64, Top 128, and Top 512 finishes. Data is Masters-only and
uses the established Performance Index definition.
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

CUTS = [64, 128, 512]


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
    """Prompt for archetype or variant rows."""
    print("\nShow conversion by:\n")
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


def select_display_count(max_count):
    """Prompt for the number of groups to display; zero means all."""
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


def _group_label(row, grouping):
    if grouping == "archetype":
        return row["overall"]
    variant = row["variant"]
    if pd.isna(variant) or variant in ("", "Default"):
        return row["overall"]
    return f"{row['overall']} — {variant}"


def build_report(results, grouping="archetype", cuts=CUTS):
    """Build cumulative top-cut counts and Performance Index values."""
    if results.empty:
        return pd.DataFrame()

    results = results.copy()
    results["standing"] = pd.to_numeric(results["standing"], errors="coerce")
    results = results.dropna(subset=["player_key", "overall", "standing"])
    results["Group"] = results.apply(lambda row: _group_label(row, grouping), axis=1)
    results = results.drop_duplicates(subset=["player_key", "Group"])
    total_players = results["player_key"].nunique()
    if not total_players:
        return pd.DataFrame()

    report = (
        results.groupby("Group")
        .agg(Players=("player_key", "nunique"))
        .reset_index()
    )
    report["Meta Share"] = report["Players"] / total_players * 100

    for cut in cuts:
        counts = (
            results[results["standing"] <= cut]
            .groupby("Group")["player_key"]
            .nunique()
            .reindex(report["Group"], fill_value=0)
            .astype(int)
            .to_numpy()
        )
        report[f"Top {cut}"] = counts
        expected_share = report["Players"] / total_players
        report[f"PI Top {cut}"] = (counts / cut) / expected_share

    report = report.sort_values(
        ["PI Top 512", "PI Top 128", "PI Top 64", "Meta Share", "Group"],
        ascending=[False, False, False, False, True],
    )
    return report.reset_index(drop=True)


def _pi_color(value):
    if value >= 1.15:
        return "#2F7D4A"
    if value <= 0.85:
        return BRAND_COLOR
    return "#8A741C"


def _format_cut(count, pi):
    if not count:
        return "—"
    return f"{int(count)}  |  {pi:.2f}x"


def create_chart(report, tournament_name, grouping, total_players):
    """Create the cumulative top-cut conversion table."""
    row_count = len(report)
    figure_height = max(9.0, 4.5 + row_count * 0.34)
    fig = plt.figure(figsize=(16, figure_height), dpi=300)
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.text(0.05, 0.965, "Top Cut Conversion", fontsize=25, fontweight="bold",
             color=TEXT_COLOR, ha="left", va="top")
    grouping_label = "Archetype" if grouping == "archetype" else "Variant"
    fig.text(
        0.05, 0.928,
        f"{tournament_name}  •  {grouping_label} view  •  {total_players} Masters decklists  •  cumulative finishes",
        fontsize=13, color=SECONDARY_TEXT_COLOR, ha="left", va="top",
    )
    fig.text(0.95, 0.965, "PTCG Data Viz", fontsize=18, fontweight="bold",
             color=BRAND_DARK, ha="right", va="top")

    left, right = 0.05, 0.95
    top, bottom = 0.865, 0.13
    widths = [0.28, 0.10, 0.13, 0.163, 0.163, 0.164]
    headers = ["Archetype / Variant" if grouping == "variant" else "Archetype",
               "Players", "Meta Share", "Top 64", "Top 128", "Top 512"]
    table_width = right - left
    row_height = (top - bottom) / max(row_count + 1, 1)
    x_positions = [left]
    for width in widths[:-1]:
        x_positions.append(x_positions[-1] + table_width * width)

    header_y = top - row_height / 2
    for index, header in enumerate(headers):
        x = x_positions[index]
        width = table_width * widths[index]
        fig.text(x + width / 2, header_y, header, fontsize=9, fontweight="bold",
                 color=BRAND_DARK, ha="center", va="center")

    fig._conversion_header = (left, top - row_height, right, top, BRAND_DARK)
    fig._conversion_lines = []
    for row_index, (_, row) in enumerate(report.iterrows()):
        y = top - (row_index + 1.5) * row_height
        values = [
            row["Group"],
            f"{int(row['Players'])}",
            f"{row['Meta Share']:.2f}%",
            _format_cut(row["Top 64"], row["PI Top 64"]),
            _format_cut(row["Top 128"], row["PI Top 128"]),
            _format_cut(row["Top 512"], row["PI Top 512"]),
        ]
        colors = [TEXT_COLOR, TEXT_COLOR, TEXT_COLOR,
                  _pi_color(row["PI Top 64"]), _pi_color(row["PI Top 128"]),
                  _pi_color(row["PI Top 512"])]
        for index, value in enumerate(values):
            x = x_positions[index]
            width = table_width * widths[index]
            fig.text(x + width / 2, y, str(value), fontsize=8.5,
                     fontweight="bold" if index >= 3 else "normal",
                     color=colors[index], ha="center", va="center")
        fig._conversion_lines.append((left, y - row_height / 2, right, y - row_height / 2))

    fig.text(left, 0.08,
             "Each cell shows cumulative finishes through the cut, followed by Performance Index.",
             fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom")
    fig.text(left, 0.05,
             "1.00x = expected representation  •  >1.00x = overrepresented  •  <1.00x = underrepresented",
             fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom")
    return fig


def add_table_overlays(output_path, fig):
    """Add table borders after export."""
    from PIL import Image, ImageDraw

    image = Image.open(output_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    def point(x, y):
        return int(x * width), int((1 - y) * height)

    left, bottom, right, top, color = fig._conversion_header
    for y in (bottom, top):
        draw.line([point(left, y), point(right, y)], fill=color,
                  width=max(2, int(width / 700)))
    for x1, y1, x2, y2 in fig._conversion_lines:
        draw.line([point(x1, y1), point(x2, y2)], fill=BORDER_COLOR,
                  width=max(1, int(width / 1800)))
    image.save(output_path)


def main():
    tournament_id, tournament_name = select_tournament()
    results = get_tournament_results(tournament_id)
    grouping = select_grouping()
    report = build_report(results, grouping=grouping)
    if report.empty:
        print("No tournament results found.")
        return

    display_count = select_display_count(len(report))
    if display_count is not None:
        report = report.head(display_count).copy()

    print()
    print(report.to_string(index=False))
    fig = create_chart(report, tournament_name, grouping, results["player_key"].nunique())
    output_path = save_chart(
        fig,
        "top_cut_conversion.png",
        output_directory=OUTPUT_DIRECTORY,
        bbox_inches=None,
        facecolor=BACKGROUND_COLOR,
        opaque_background=True,
    )
    add_table_overlays(output_path, fig)
    plt.close(fig)
    print(f"\nChart saved to:\n{output_path}")


if __name__ == "__main__":
    main()
