"""
Performance Index timeline visualization.

Displays actual or cumulative Performance Index by tournament for selected
archetypes or variants. The calculations match the existing analytics report.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analytics_queries import get_all_tournament_results, get_tournaments
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


def select_tournaments():
    """Prompt for one or more tournaments."""
    tournaments = get_tournaments()

    print("\nAvailable Tournaments:\n")
    for index, row in tournaments.iterrows():
        print(f"{index + 1}. {row['tournament_name']}")

    while True:
        try:
            choices = input("\nSelect tournaments (comma separated): ")
            indices = [int(value.strip()) - 1 for value in choices.split(",")]
            if indices and all(0 <= index < len(tournaments) for index in indices):
                return tournaments.iloc[indices].sort_values("start_date")
        except ValueError:
            pass
        print("Please enter valid tournament numbers separated by commas.")


def select_grouping():
    """Prompt for archetype or variant grouping."""
    print("\nShow Performance Index by:\n")
    print("1. Archetype")
    print("2. Variant")

    while True:
        try:
            choice = int(input("\nSelect grouping: "))
            if choice == 1:
                return "overall"
            if choice == 2:
                return "variant"
        except ValueError:
            pass
        print("Please enter 1 or 2.")


def select_archetypes(results):
    """Prompt for one or more archetypes in variant mode."""
    archetypes = sorted(results["overall"].dropna().unique())

    print("\nAvailable Archetypes:\n")
    for index, archetype in enumerate(archetypes, start=1):
        print(f"{index}. {archetype}")

    while True:
        try:
            choices = input("\nSelect archetypes (comma separated): ")
            indices = [int(value.strip()) - 1 for value in choices.split(",")]
            if indices and all(0 <= index < len(archetypes) for index in indices):
                return [archetypes[index] for index in indices]
        except ValueError:
            pass
        print("Please enter valid archetype numbers separated by commas.")


def select_cut():
    """Prompt for the PI cut."""
    print("\nPerformance Index cut:\n")
    for index, cut in enumerate(CUTS, start=1):
        print(f"{index}. Top {cut}")

    while True:
        try:
            choice = int(input("\nSelect cut: "))
            if 1 <= choice <= len(CUTS):
                return CUTS[choice - 1]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(CUTS)}.")


def select_performance_type():
    """Prompt for actual or cumulative PI."""
    print("\nPerformance Index type:\n")
    print("1. Actual")
    print("2. Cumulative")

    while True:
        try:
            choice = int(input("\nSelect type: "))
            if choice == 1:
                return False
            if choice == 2:
                return True
        except ValueError:
            pass
        print("Please enter 1 or 2.")


def select_display_count(max_count, grouping):
    """Prompt for the number of groups to display."""
    label = "archetypes" if grouping == "overall" else "variants"
    print(f"\nHow many {label} should be displayed?\n")
    print("0. All groups")

    while True:
        try:
            choice = int(input(f"\nSelect 0-{max_count}: "))
            if 0 <= choice <= max_count:
                return None if choice == 0 else choice
        except ValueError:
            pass
        print(f"Please enter a whole number from 0 to {max_count}.")


def _display_name(overall, variant):
    if variant in (None, "", "Default"):
        return overall
    return f"{overall} — {variant}"


def _performance_index(players, total_players, top_cut_players, denominator):
    if players == 0 or total_players == 0:
        return 0.0
    expected = (players / total_players) * denominator
    if expected == 0:
        return 0.0
    return top_cut_players / expected


def build_report(tournaments, results, grouping, cut, cumulative, archetypes=None):
    """Build the PI timeline using the established analytics definition."""
    filtered = results.copy()
    if grouping == "variant" and archetypes:
        filtered = filtered[filtered["overall"].isin(archetypes)].copy()

    previous_cut = {64: 32, 128: 64, 512: 256}[cut]
    denominator = cut if cumulative else cut - previous_cut
    rows = []

    for _, tournament in tournaments.iterrows():
        tournament_df = filtered[
            filtered["tournament_id"] == tournament["tournament_id"]
        ].copy()
        total_players = len(tournament_df)
        if total_players == 0:
            continue

        if grouping == "overall":
            tournament_df["Group"] = tournament_df["overall"]
        else:
            tournament_df["Group"] = tournament_df.apply(
                lambda row: _display_name(row["overall"], row["variant"]),
                axis=1,
            )

        for group, group_df in tournament_df.groupby("Group"):
            players = len(group_df)
            if cumulative:
                top_cut_players = (group_df["standing"] <= cut).sum()
            else:
                top_cut_players = (
                    (group_df["standing"] > previous_cut)
                    & (group_df["standing"] <= cut)
                ).sum()

            rows.append(
                {
                    "Group": group,
                    "Tournament": tournament["tournament_name"],
                    "PI": _performance_index(
                        players,
                        total_players,
                        top_cut_players,
                        denominator,
                    ),
                }
            )

    report = pd.DataFrame(rows)
    if report.empty:
        return report, []

    tournament_order = tournaments["tournament_name"].tolist()
    pivot = report.pivot(index="Group", columns="Tournament", values="PI")
    pivot = pivot.reindex(columns=tournament_order, fill_value=0).fillna(0).reset_index()
    pivot["_last"] = pivot[tournament_order[-1]]
    pivot["_mean"] = pivot[tournament_order].mean(axis=1)
    pivot = pivot.sort_values(["_last", "_mean", "Group"], ascending=[False, False, True])
    return pivot.drop(columns=["_last", "_mean"]).reset_index(drop=True), tournament_order


def _pi_color(value):
    if value >= 1.15:
        return "#2F7D4A"
    if value <= 0.85:
        return "#A6192E"
    return "#8A741C"


def _trend(values):
    if len(values) < 2:
        return "NEUTRAL"
    change = values[-1] - values[0]
    if change >= 0.15:
        return "RISING"
    if change <= -0.15:
        return "FALLING"
    return "NEUTRAL"


def create_chart(report, tournament_order, grouping, cut, cumulative, archetypes=None, top_n=None):
    """Create the PI timeline table."""
    row_count = len(report)
    figure_height = max(9.0, 4.5 + row_count * 0.31)
    fig = plt.figure(figsize=(16, figure_height), dpi=300)
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    title = "Performance Index Timeline"
    grouping_label = "Archetype" if grouping == "overall" else "Variant"
    mode_label = "Cumulative" if cumulative else "Actual"
    if archetypes:
        scope_name = ", ".join(archetypes) if len(archetypes) <= 3 else f"{len(archetypes)} selected archetypes"
        scope = f"{scope_name}  •  "
    else:
        scope = ""
    subtitle = f"{scope}{grouping_label} view  •  Top {cut}  •  {mode_label}"

    fig.text(0.05, 0.965, title, fontsize=25, fontweight="bold", color=TEXT_COLOR, ha="left", va="top")
    fig.text(0.05, 0.928, subtitle, fontsize=13, color=SECONDARY_TEXT_COLOR, ha="left", va="top")
    fig.text(0.95, 0.965, "PTCG Data Viz", fontsize=18, fontweight="bold", color=BRAND_DARK, ha="right", va="top")

    left, right = 0.05, 0.95
    top, bottom = 0.87, 0.145
    table_width = right - left
    row_height = (top - bottom) / max(row_count + 1, 1)
    group_width = 0.28
    trend_width = 0.13
    value_width = (1 - group_width - trend_width) / max(len(tournament_order), 1)
    widths = [group_width] + [value_width] * len(tournament_order) + [trend_width]
    headers = ["Archetype" if grouping == "overall" else "Archetype / Variant"] + tournament_order + ["Trend"]
    x_positions = [left]
    for width in widths[:-1]:
        x_positions.append(x_positions[-1] + table_width * width)

    fig._pi_lines = []
    fig._pi_header = (left, top - row_height, right, top, BRAND_DARK)
    for index, header in enumerate(headers):
        x = x_positions[index]
        width = table_width * widths[index]
        fig.text(x + width / 2, top - row_height / 2, header, fontsize=9, fontweight="bold", color=BRAND_DARK, ha="center", va="center")

    for row_index, (_, row) in enumerate(report.iterrows()):
        y = top - (row_index + 1.5) * row_height
        values = [row["Group"]] + [f"{row[name]:.2f}x" for name in tournament_order]
        values.append(_trend([row[name] for name in tournament_order]))

        for index, value in enumerate(values):
            x = x_positions[index]
            width = table_width * widths[index]
            if index == 0:
                color = TEXT_COLOR
            elif index <= len(tournament_order):
                color = _pi_color(float(row[tournament_order[index - 1]]))
            else:
                color = {"RISING": "#2F7D4A", "FALLING": BRAND_COLOR}.get(value, SECONDARY_TEXT_COLOR)
            fig.text(x + width / 2, y, str(value), fontsize=8.5, fontweight="bold" if index > 0 else "normal", color=color, ha="center", va="center")

        fig._pi_lines.append((left, y - row_height / 2, right, y - row_height / 2))

    display_text = "All groups" if top_n is None else f"Top {top_n} groups"
    fig.text(left, 0.095, f"{display_text} shown, ranked by the latest selected tournament.", fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom")
    fig.text(left, 0.065, "1.00x = expected representation  •  >1.00x = overrepresented  •  <1.00x = underrepresented", fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom")
    fig.text(left, 0.035, "Actual uses only the selected finish range; cumulative includes all finishes through the selected cut.", fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom")
    return fig


def add_pi_overlays(output_path, fig):
    """Add table rules with Pillow after export."""
    from PIL import Image, ImageDraw

    image = Image.open(output_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    def point(x, y):
        return int(x * width), int((1 - y) * height)

    left, bottom, right, top, color = fig._pi_header
    for y in (bottom, top):
        draw.line([point(left, y), point(right, y)], fill=color, width=max(2, int(width / 700)))
    for x1, y1, x2, y2 in fig._pi_lines:
        draw.line([point(x1, y1), point(x2, y2)], fill=BORDER_COLOR, width=max(1, int(width / 1800)))
    image.save(output_path)


def main():
    tournaments = select_tournaments()
    grouping = select_grouping()
    cut = select_cut()
    cumulative = select_performance_type()
    results = get_all_tournament_results()

    archetypes = None
    if grouping == "variant":
        archetypes = select_archetypes(results)

    report, tournament_order = build_report(tournaments, results, grouping, cut, cumulative, archetypes)
    if report.empty:
        print("No Performance Index data found.")
        return

    display_count = select_display_count(len(report), grouping)
    if display_count is not None:
        report = report.head(display_count).copy()

    print(report.to_string(index=False))
    fig = create_chart(report, tournament_order, grouping, cut, cumulative, archetypes, display_count)
    output_path = save_chart(
        fig,
        "performance_index_timeline.png",
        output_directory=OUTPUT_DIRECTORY,
        bbox_inches=None,
        facecolor=BACKGROUND_COLOR,
        opaque_background=True,
    )
    add_pi_overlays(output_path, fig)
    plt.close(fig)
    print(f"\nChart saved to:\n{output_path}")


if __name__ == "__main__":
    main()
