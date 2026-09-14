"""
Archetype comparison visualization.

Compares selected archetypes within one tournament across:
- Players
- Meta Share
- Average Finish
- Performance Index at Top 64, Top 128, and Top 512

The visualization uses a clean comparison table with conditional
formatting focused on the metrics where color adds analytical meaning.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.analytics_queries import (
    get_tournaments,
    get_archetype_summary,
)

from src.visualizations.chart_style import (
    FIGURE_SIZE,
    DPI,
    BACKGROUND_COLOR,
    BRAND_COLOR,
    BRAND_DARK,
    TEXT_COLOR,
    SECONDARY_TEXT_COLOR,
    GRID_COLOR,
    BORDER_COLOR,
    TITLE_SIZE,
    SUBTITLE_SIZE,
    LABEL_SIZE,
    TICK_SIZE,
)


CUTS = [
    8,
    16,
    32,
    64,
    128,
    256,
    512,
]


# ---------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------

def select_tournament():
    """
    Let the user choose a tournament.
    """

    tournaments = get_tournaments()

    print()
    print("=" * 60)
    print("TOURNAMENTS")
    print("=" * 60)

    for i, row in tournaments.iterrows():
        print(
            f"{i + 1}. "
            f"{row['tournament_name']}"
        )

    choice = int(
        input("\nSelect tournament: ")
    )

    tournament = tournaments.iloc[
        choice - 1
    ]

    return (
        tournament["tournament_id"],
        tournament["tournament_name"],
    )


def select_archetypes(df):
    """
    Let the user choose 2-5 archetypes.
    """

    archetypes = sorted(
        df["overall"]
        .dropna()
        .unique()
    )

    print()
    print("=" * 60)
    print("ARCHETYPES")
    print("=" * 60)

    for i, archetype in enumerate(
        archetypes,
        start=1,
    ):
        print(
            f"{i}. {archetype}"
        )

    number = int(
        input(
            "\nHow many archetypes (2-5)? "
        )
    )

    if number < 2 or number > 5:
        raise ValueError(
            "Please select between 2 and 5 archetypes."
        )

    selected = []

    for i in range(number):
        choice = int(
            input(
                f"Select archetype #{i + 1}: "
            )
        )

        selected.append(
            archetypes[
                choice - 1
            ]
        )

    if len(set(selected)) != len(selected):
        raise ValueError(
            "Each archetype can only be selected once."
        )

    return selected


def select_performance_type():
    """
    Select actual or cumulative Performance Index.
    """

    print()
    print("=" * 60)
    print("PERFORMANCE INDEX")
    print("=" * 60)
    print("1. Actual")
    print("2. Cumulative")

    choice = int(
        input("\nSelect: ")
    )

    if choice not in (1, 2):
        raise ValueError(
            "Please select 1 or 2."
        )

    return choice == 2


# ---------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------

def performance_index(
    archetype_players,
    total_players,
    top_cut_players,
    cut_size,
):
    """
    Calculate Performance Index.
    """

    if archetype_players == 0:
        return 0.0

    expected = (
        archetype_players
        / total_players
    ) * cut_size

    if expected == 0:
        return 0.0

    return (
        top_cut_players
        / expected
    )


def build_report(
    df,
    archetypes,
    cumulative,
):
    """
    Build the comparison report using the existing analytics logic.
    """

    total_players = len(df)

    metrics = []

    for archetype in archetypes:

        deck_df = df[
            df["overall"] == archetype
        ]

        row = {
            "Archetype": archetype,
            "Players": len(deck_df),
            "Meta Share":
                len(deck_df)
                / total_players
                * 100,
            "Average Finish":
                deck_df["standing"].mean(),
        }

        previous_cut = 0

        pi_values = {}

        for cut in CUTS:

            if cumulative:

                count = len(
                    deck_df[
                        deck_df["standing"] <= cut
                    ]
                )

                denominator = cut

            else:

                count = len(
                    deck_df[
                        (
                            deck_df["standing"]
                            > previous_cut
                        )
                        &
                        (
                            deck_df["standing"]
                            <= cut
                        )
                    ]
                )

                denominator = (
                    cut
                    - previous_cut
                )

            pi_values[cut] = performance_index(
                len(deck_df),
                total_players,
                count,
                denominator,
            )

            previous_cut = cut

        row["PI Top 64"] = pi_values[64]
        row["PI Top 128"] = pi_values[128]
        row["PI Top 512"] = pi_values[512]

        metrics.append(row)

    report = pd.DataFrame(metrics)

    report = report.sort_values(
        "Meta Share",
        ascending=False,
    ).reset_index(drop=True)

    return report


# ---------------------------------------------------------------------
# Conditional formatting
# ---------------------------------------------------------------------

def blend_color(
    low_color,
    high_color,
    value,
):
    """
    Blend two RGB colors using value from 0 to 1.
    """

    low = np.array(
        plt.matplotlib.colors.to_rgb(
            low_color
        )
    )

    high = np.array(
        plt.matplotlib.colors.to_rgb(
            high_color
        )
    )

    value = max(
        0,
        min(1, value),
    )

    result = (
        low
        + (high - low) * value
    )

    return tuple(result)


def heatmap_color(
    value,
    minimum,
    maximum,
):
    """
    Green -> yellow -> red conditional formatting.

    Higher values are greener.
    Lower values are redder.
    """

    if maximum == minimum:
        return "#F2F2F2"

    midpoint = (
        minimum + maximum
    ) / 2

    if value <= midpoint:

        ratio = (
            value - minimum
        ) / (
            midpoint - minimum
        )

        return blend_color(
            "#E7B8B8",
            "#FFF2C7",
            ratio,
        )

    ratio = (
        value - midpoint
    ) / (
        maximum - midpoint
    )

    return blend_color(
        "#FFF2C7",
        "#BFDDBF",
        ratio,
    )


def pi_color(value):
    """
    Conditional formatting for Performance Index.

    1.00x is the meaningful midpoint:
    - Above 1.00x = green
    - Around 1.00x = neutral
    - Below 1.00x = red
    """

    neutral = "#F3F3F1"
    green = "#CFE5CF"
    red = "#E8C5C5"

    if value >= 1.0:

        distance = min(
            (value - 1.0) / 0.75,
            1.0,
        )

        return blend_color(
            neutral,
            green,
            distance,
        )

    distance = min(
        (1.0 - value) / 0.75,
        1.0,
    )

    return blend_color(
        neutral,
        red,
        distance,
    )


def finish_color(value, minimum, maximum):
    """
    Conditional formatting for Average Finish.

    Lower finish number is better, so:
    - Lower = green
    - Middle = yellow
    - Higher = red
    """

    if maximum == minimum:
        return "#F3F3F1"

    # Reverse the scale because a lower finish is better.
    return heatmap_color(
        maximum + minimum - value,
        minimum,
        maximum,
    )


# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------

def draw_comparison(
    report,
    tournament_name,
    cumulative,
):
    """
    Draw the Archetype Comparison visualization.
    """

    fig = plt.figure(
        figsize=FIGURE_SIZE,
        dpi=DPI,
    )

    fig.patch.set_facecolor(
        BACKGROUND_COLOR
    )

    # -------------------------------------------------------------
    # Header
    # -------------------------------------------------------------

    title = "Archetype Comparison"

    subtitle = (
        f"{tournament_name} | "
        f"{'Cumulative' if cumulative else 'Actual'} Performance Index"
    )

    fig.text(
        0.04,
        0.94,
        title,
        fontsize=TITLE_SIZE,
        fontweight="bold",
        color=TEXT_COLOR,
        ha="left",
        va="top",
    )

    fig.text(
        0.04,
        0.895,
        subtitle,
        fontsize=SUBTITLE_SIZE,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="top",
    )

    fig.text(
        0.96,
        0.94,
        "PTCG Data Viz",
        fontsize=TITLE_SIZE - 2,
        fontweight="bold",
        color=BRAND_DARK,
        ha="right",
        va="top",
    )

    # -------------------------------------------------------------
    # Table geometry
    # -------------------------------------------------------------

    left = 0.04
    right = 0.96
    top = 0.81
    bottom = 0.20

    table_width = right - left
    table_height = top - bottom

    headers = [
        "Archetype",
        "Players",
        "Meta Share",
        "Average Finish",
        "PI Top 64",
        "PI Top 128",
        "PI Top 512",
    ]

    column_widths = [
        0.24,
        0.10,
        0.12,
        0.14,
        0.133,
        0.133,
        0.133,
    ]

    # Normalize widths to exactly fill the table.
    width_sum = sum(column_widths)

    column_widths = [
        width / width_sum
        for width in column_widths
    ]

    n_rows = len(report)

    header_height = (
        table_height
        * 0.12
    )

    row_height = (
        table_height
        - header_height
    ) / n_rows

    # -------------------------------------------------------------
    # Header row
    # -------------------------------------------------------------

    x_cursor = left

    for index, header in enumerate(headers):

        width = (
            table_width
            * column_widths[index]
        )

        rect = Rectangle(
            (
                x_cursor,
                top - header_height,
            ),
            width,
            header_height,
            transform=fig.transFigure,
            facecolor=BRAND_DARK,
            edgecolor=BACKGROUND_COLOR,
            linewidth=1.5,
            zorder=1,
        )

        fig.add_artist(rect)

        fig.text(
            x_cursor + width / 2,
            top - header_height / 2,
            header,
            fontsize=LABEL_SIZE,
            fontweight="bold",
            color="white",
            ha="center",
            va="center",
        )

        x_cursor += width

    # -------------------------------------------------------------
    # Data ranges for conditional formatting
    # -------------------------------------------------------------

    meta_min = report["Meta Share"].min()
    meta_max = report["Meta Share"].max()

    finish_min = report["Average Finish"].min()
    finish_max = report["Average Finish"].max()

    pi_columns = [
        "PI Top 64",
        "PI Top 128",
        "PI Top 512",
    ]

    # -------------------------------------------------------------
    # Data rows
    # -------------------------------------------------------------

    for row_index, (_, row) in enumerate(
        report.iterrows()
    ):

        y = (
            top
            - header_height
            - (
                row_index + 1
            ) * row_height
        )

        x_cursor = left

        values = [
            row["Archetype"],
            f"{row['Players']:.0f}",
            f"{row['Meta Share']:.1f}%",
            f"{row['Average Finish']:.0f}",
            f"{row['PI Top 64']:.2f}x",
            f"{row['PI Top 128']:.2f}x",
            f"{row['PI Top 512']:.2f}x",
        ]

        for column_index, value in enumerate(values):

            width = (
                table_width
                * column_widths[
                    column_index
                ]
            )

            # -----------------------------------------------------
            # Base cell
            # -----------------------------------------------------

            facecolor = "#F7F7F5"

            if column_index == 2:
                facecolor = heatmap_color(
                    row["Meta Share"],
                    meta_min,
                    meta_max,
                )

            elif column_index == 3:
                facecolor = finish_color(
                    row["Average Finish"],
                    finish_min,
                    finish_max,
                )

            elif column_index >= 4:
                facecolor = pi_color(
                    row[
                        pi_columns[
                            column_index - 4
                        ]
                    ]
                )

            rect = Rectangle(
                (
                    x_cursor,
                    y,
                ),
                width,
                row_height,
                transform=fig.transFigure,
                facecolor=facecolor,
                edgecolor=BACKGROUND_COLOR,
                linewidth=1.5,
                zorder=1,
            )

            fig.add_artist(rect)

            # -----------------------------------------------------
            # Text alignment
            # -----------------------------------------------------

            # Center the archetype name just like the other
            # comparison values. This keeps the table visually
            # balanced and makes side-by-side comparison easier.
            ha = "center"
            text_x = (
                x_cursor
                + width / 2
            )

            fontweight = (
                "bold"
                if column_index >= 2
                else "normal"
            )

            fig.text(
                text_x,
                y + row_height / 2,
                str(value),
                fontsize=LABEL_SIZE,
                fontweight=fontweight,
                color=TEXT_COLOR,
                ha=ha,
                va="center",
                zorder=2,
            )

            x_cursor += width

    # -------------------------------------------------------------
    # How to read
    # -------------------------------------------------------------

    fig.text(
        0.04,
        0.105,
        "HOW TO READ",
        fontsize=10,
        fontweight="bold",
        color=BRAND_DARK,
        ha="left",
        va="bottom",
    )

    pi_note_1 = (
        "Performance Index (PI) compares an archetype's share of "
        "top-cut finishes with its expected share based on meta share."
    )

    pi_note_2 = (
        "For example, 2.00x means an archetype reached a cut at twice "
        "its expected rate; 0.50x means half its expected rate."
    )

    pi_note_3 = (
        "1.00x = expected representation  |  "
        ">1.00x = overrepresented  |  "
        "<1.00x = underrepresented"
    )

    pi_note_4 = (
        "Cumulative includes all finishes through each cut; "
        "Actual measures only finishes within that cut range."
    )

    fig.text(
        0.04,
        0.078,
        pi_note_1,
        fontsize=10,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.04,
        0.052,
        pi_note_2,
        fontsize=10,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.04,
        0.026,
        pi_note_3,
        fontsize=10,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.04,
        0.008,
        pi_note_4,
        fontsize=10,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
    )

    # -------------------------------------------------------------
    # Export-safe figure settings
    # -------------------------------------------------------------

    fig.subplots_adjust(
        left=0,
        right=1,
        top=1,
        bottom=0,
    )

    return fig


# ---------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------

def save_chart(
    fig,
    filename,
    output_directory="output/visualizations",
):
    """
    Save chart using the project's standard export settings.
    """

    from pathlib import Path

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / filename
    )

    fig.savefig(
        output_path,
        dpi=DPI,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )

    return output_path


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    tournament_id, tournament_name = (
        select_tournament()
    )

    df = get_archetype_summary(
        tournament_id
    )

    archetypes = select_archetypes(
        df
    )

    cumulative = (
        select_performance_type()
    )

    report = build_report(
        df,
        archetypes,
        cumulative,
    )

    print()
    print("=" * 60)
    print(tournament_name)
    print("ARCHETYPE COMPARISON")
    print("=" * 60)
    print()

    print(
        report.to_string(
            index=False,
            formatters={
                "Players":
                    "{:.0f}".format,
                "Meta Share":
                    "{:.1f}%".format,
                "Average Finish":
                    "{:.0f}".format,
                "PI Top 64":
                    "{:.2f}x".format,
                "PI Top 128":
                    "{:.2f}x".format,
                "PI Top 512":
                    "{:.2f}x".format,
            },
        )
    )

    fig = draw_comparison(
        report,
        tournament_name,
        cumulative,
    )

    filename = (
        "archetype_comparison.png"
    )

    output_path = save_chart(
        fig,
        filename,
    )

    print()
    print(
        f"Saved visualization: {output_path}"
    )

    plt.show()


if __name__ == "__main__":
    main()
