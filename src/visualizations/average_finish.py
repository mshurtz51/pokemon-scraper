"""
Average Finish Distribution Visualization
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from src.analytics_queries import (
    get_tournaments,
    get_tournament_results,
)

from src.visualizations.chart_style import (
    BACKGROUND_COLOR,
    BRAND_COLOR,
    BRAND_DARK,
    TEXT_COLOR,
    SECONDARY_TEXT_COLOR,
    BORDER_COLOR,
    LABEL_SIZE,
    OVERVIEW_LABEL_SIZE,
    OVERVIEW_VALUE_SIZE,
    setup_chart,
    style_axes,
    save_chart,
)


FINISH_BANDS = [
    (1, 64, "Top 64"),
    (65, 128, "65–128"),
    (129, 512, "129–512"),
    (513, 1024, "513–1,024"),
    (1025, 1499, "1,025–1,499"),
    (1500, 2499, "1,500–2,499"),
    (2500, 3499, "2,500–3,499"),
    (3500, None, "3,500+"),
]



def select_tournament():
    """Display tournaments and return the selected tournament."""
    tournaments = get_tournaments()

    print("\nAvailable Tournaments:\n")

    for i, row in tournaments.iterrows():
        print(f"{i + 1}. {row['tournament_name']}")

    while True:
        try:
            selection = int(input("\nSelect tournament: "))

            if 1 <= selection <= len(tournaments):
                break

            print(
                f"Please enter a number between 1 and "
                f"{len(tournaments)}."
            )

        except ValueError:
            print("Please enter a valid number.")

    tournament = tournaments.iloc[selection - 1]

    return (
        tournament["tournament_id"],
        tournament["tournament_name"],
    )



def select_grouping():
    """Prompt the user to select overall archetype or variant grouping."""
    print("\nGroup By:\n")
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


def select_number_of_groups(max_groups, grouping):
    """Select how many of the most-played groups to display."""
    label = "archetypes" if grouping == "overall" else "variants"

    print(f"\nNumber of {label} available: {max_groups}")

    while True:
        try:
            number = int(
                input(
                    f"How many {label} would you like to display? "
                )
            )

            if 1 <= number <= max_groups:
                return number

            print(
                f"Please enter a number between 1 and {max_groups}."
            )

        except ValueError:
            print("Please enter a valid number.")



def build_summary(df, grouping="overall"):
    """Build the finish summary at the selected archetype/variant level."""
    if grouping == "overall":
        summary = (
            df.groupby("overall")
            .agg(
                Players=("overall", "size"),
                Average_Finish=("standing", "mean"),
                Median_Finish=("standing", "median"),
            )
            .reset_index()
        )

        summary["Display_Name"] = summary["overall"]
        summary["Group_Key"] = summary["overall"]
        return summary

    summary = (
        df.groupby(["overall", "variant"])
        .agg(
            Players=("variant", "size"),
            Average_Finish=("standing", "mean"),
            Median_Finish=("standing", "median"),
        )
        .reset_index()
    )

    summary["Display_Name"] = (
        summary["overall"]
        + summary["variant"].apply(
            lambda x: "" if x == "Default" else f" — {x}"
        )
    )
    summary["Group_Key"] = list(
        zip(summary["overall"], summary["variant"])
    )

    return summary



def prepare_chart_data(summary, number_of_groups, grouping):
    """Select the most represented groups, then order by average finish."""
    selected = (
        summary
        .sort_values(
            ["Players", "Average_Finish"],
            ascending=[False, True],
        )
        .head(number_of_groups)
        .copy()
    )

    return (
        selected
        .sort_values(
            ["Average_Finish", "Median_Finish"],
            ascending=[True, True],
        )
        .reset_index(drop=True)
    )



def build_distribution_data(df, chart_data, grouping):
    """Calculate finish-band shares for each selected archetype or variant."""
    rows = []

    for _, group_row in chart_data.iterrows():
        if grouping == "overall":
            group_df = df[df["overall"] == group_row["overall"]].copy()
        else:
            group_df = df[
                (df["overall"] == group_row["overall"])
                & (df["variant"] == group_row["variant"])
            ].copy()

        players = len(group_df)

        row = {
            "Display_Name": group_row["Display_Name"],
            "Players": players,
            "Average_Finish": group_row["Average_Finish"],
            "Median_Finish": group_row["Median_Finish"],
        }

        for lower, upper, label in FINISH_BANDS:
            if upper is None:
                count = int(
                    (group_df["standing"] >= lower).sum()
                )
            else:
                count = int(
                    group_df["standing"]
                    .between(lower, upper, inclusive="both")
                    .sum()
                )

            row[label] = (count / players * 100) if players else 0

        rows.append(row)

    return rows



def create_heatmap_cmap():
    """Create a red-to-yellow-to-green concentration heatmap."""
    return LinearSegmentedColormap.from_list(
        "finish_distribution",
        [
            "#C62828",
            "#F4D35E",
            "#2E7D32",
        ],
    )


def calculate_field_adjusted_index(
    raw_percentage,
    lower,
    upper,
    total_players,
):
    """Compare archetype concentration with the share of the field in a band."""
    if total_players <= 0:
        return 0.0

    if upper is None:
        band_size = max(total_players - lower + 1, 0)
    else:
        band_size = max(upper - lower + 1, 0)

    if band_size <= 0:
        return 0.0

    field_percentage = band_size / total_players * 100

    if field_percentage <= 0:
        return 0.0

    return raw_percentage / field_percentage


def draw_finish_distribution(
    distribution_data,
    tournament_name,
    total_players,
    number_of_groups,
    grouping,
):
    """Draw the finish-distribution heatmap."""
    group_label = "Archetypes" if grouping == "overall" else "Variants"

    fig, ax = setup_chart(
        title="Finish Distribution",
        subtitle=(
            f"{tournament_name} | "
            f"Top {number_of_groups} {group_label} by Player Count"
        ),
    )

    fig.text(
        0.965,
        0.965,
        "PTCG Data Viz",
        fontsize=14,
        fontweight="bold",
        color=BRAND_COLOR,
        ha="right",
        va="top",
    )

    # Main table area. Extra vertical space keeps the context and headers separate.
    left = 0.20
    right = 0.965
    top = 0.77
    bottom = 0.20

    ax.set_position([left, bottom, right - left, top - bottom])
    ax.set_xlim(0, 11.7)
    ax.set_ylim(-0.5, len(distribution_data) - 0.5)
    ax.invert_yaxis()

    heatmap_start = 1.0
    heatmap_width = 1.0
    summary_start = heatmap_start + len(FINISH_BANDS) + 0.35
    average_x = summary_start + 0.65
    median_x = summary_start + 1.55

    cmap = create_heatmap_cmap()

    # Calculate field-adjusted concentration for color scaling.
    # 1.0x means the archetype is represented in a band exactly in proportion
    # to the number of tournament finishing positions contained in that band.
    all_indices = []
    for row in distribution_data:
        for lower, upper, label in FINISH_BANDS:
            index = calculate_field_adjusted_index(
                row[label],
                lower,
                upper,
                total_players,
            )
            all_indices.append(index)

    max_index = max(all_indices) if all_indices else 1.0
    color_norm = TwoSlopeNorm(
        vmin=0.0,
        vcenter=1.0,
        vmax=max(max_index, 1.05),
    )

    for y, row in enumerate(distribution_data):
        # Archetype label and player count.
        ax.text(
            0.94,
            y - 0.07,
            row["Display_Name"],
            fontsize=LABEL_SIZE,
            fontweight="bold",
            color=TEXT_COLOR,
            ha="right",
            va="center",
        )

        ax.text(
            0.94,
            y + 0.27,
            f"{row['Players']:,} players",
            fontsize=9,
            color=SECONDARY_TEXT_COLOR,
            ha="right",
            va="center",
        )

        values = [row[label] for _, _, label in FINISH_BANDS]
        indices = [
            calculate_field_adjusted_index(
                row[label],
                lower,
                upper,
                total_players,
            )
            for lower, upper, label in FINISH_BANDS
        ]

        max_value = max(values) if values else 0
        max_index_position = (
            indices.index(max(indices)) if indices else 0
        )

        for x_offset, (_, _, label), value, index in zip(
            range(len(FINISH_BANDS)),
            FINISH_BANDS,
            values,
            indices,
        ):
            x = heatmap_start + x_offset
            facecolor = cmap(color_norm(index))

            rectangle = Rectangle(
                (x, y - 0.39),
                heatmap_width,
                0.78,
                facecolor=facecolor,
                edgecolor=BACKGROUND_COLOR,
                linewidth=2.0,
            )
            ax.add_patch(rectangle)

            # White text works on green; dark text is clearer on yellow/red.
            text_color = (
                BACKGROUND_COLOR
                if index >= 1.55
                else TEXT_COLOR
            )

            # Show both the archetype's raw share and its field-adjusted
            # concentration. The percentage is the share of that archetype's
            # players in the band; the concentration compares that share with
            # the share of available finishing positions in the band.
            ax.text(
                x + 0.5,
                y - 0.08,
                f"{value:.0f}%",
                fontsize=9.5,
                fontweight="bold" if value == max_value else "normal",
                color=text_color,
                ha="center",
                va="center",
            )

            ax.text(
                x + 0.5,
                y + 0.18,
                f"{index:.1f}x",
                fontsize=7.8,
                color=text_color,
                alpha=0.9,
                ha="center",
                va="center",
            )

            # Outline the band's highest field-adjusted concentration.
            if x_offset == max_index_position and index > 0:
                highlight = Rectangle(
                    (x + 0.025, y - 0.365),
                    0.95,
                    0.73,
                    fill=False,
                    edgecolor=BRAND_DARK,
                    linewidth=1.4,
                )
                ax.add_patch(highlight)

        # Average and median summary columns.
        ax.text(
            average_x,
            y,
            f"{row['Average_Finish']:.0f}",
            fontsize=11,
            fontweight="bold",
            color=BRAND_DARK,
            ha="center",
            va="center",
        )

        ax.text(
            median_x,
            y,
            f"{row['Median_Finish']:.0f}",
            fontsize=11,
            color=TEXT_COLOR,
            ha="center",
            va="center",
        )

    # Column headers. Kept in a dedicated row so they cannot collide with
    # tournament-level summary information.
    for x_offset, (_, _, label) in enumerate(FINISH_BANDS):
        ax.text(
            heatmap_start + x_offset + 0.5,
            -0.93,
            label,
            fontsize=9.2,
            fontweight="bold",
            color=SECONDARY_TEXT_COLOR,
            ha="center",
            va="bottom",
        )

    ax.text(
        0.94,
        -0.93,
        "DECK",
        fontsize=9,
        fontweight="bold",
        color=SECONDARY_TEXT_COLOR,
        ha="right",
        va="bottom",
    )

    ax.text(
        average_x,
        -0.93,
        "AVG",
        fontsize=9,
        fontweight="bold",
        color=SECONDARY_TEXT_COLOR,
        ha="center",
        va="bottom",
    )

    ax.text(
        median_x,
        -0.93,
        "MEDIAN",
        fontsize=9,
        fontweight="bold",
        color=SECONDARY_TEXT_COLOR,
        ha="center",
        va="bottom",
    )

    # Tournament context line. Positioned well above the column headers so the
    # context and finish-band labels remain visually separate.
    fig.text(
        left,
        0.835,
        f"TOURNAMENT FIELD  {total_players:,} players",
        fontsize=9.5,
        fontweight="bold",
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
    )

    fig.text(
        right,
        0.835,
        f"DISPLAYED  Top {number_of_groups} {group_label.lower()} by player count",
        fontsize=9.5,
        fontweight="bold",
        color=SECONDARY_TEXT_COLOR,
        ha="right",
        va="bottom",
    )

    ax.set_xticks([])
    ax.set_yticks([])

    style_axes(
        ax,
        show_x_grid=False,
        show_y_grid=False,
    )

    for spine in ax.spines.values():
        spine.set_visible(False)

    # Explain the normalization in compact multi-line text so the note does not
    # force the saved graphic to become excessively tall.
    fig.text(
        left,
        0.045,
        (
            "CELL LABELS  =  % of the selected deck's players in the range; x-value = field-adjusted concentration.\n"
            "CONCENTRATION  =  1.0x means proportional to available finishing positions; >1.0x overrepresented; <1.0x underrepresented.\n"
            "BOLD  =  largest share of that selected deck's players.     OUTLINE  =  strongest field-adjusted range.     "
            "GREEN  =  overrepresented     YELLOW  =  near field share     RED  =  underrepresented"
        ),
        fontsize=8.5,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="bottom",
        linespacing=1.45,
    )

    return fig


def main():
    tournament_id, tournament_name = select_tournament()

    df = get_tournament_results(tournament_id)

    if df.empty:
        print("\nNo tournament data found.")
        return

    grouping = select_grouping()
    summary = build_summary(df, grouping=grouping)

    number_of_groups = select_number_of_groups(
        len(summary),
        grouping,
    )

    chart_data = prepare_chart_data(
        summary,
        number_of_groups,
        grouping,
    )

    distribution_data = build_distribution_data(
        df,
        chart_data,
        grouping,
    )

    total_players = len(df)

    print()
    print("=" * 60)
    print(tournament_name)
    print("=" * 60)
    print()

    group_label = "Archetypes" if grouping == "overall" else "Variants"

    print(
        f"Showing Top {number_of_groups} {group_label} by Player Count"
    )
    print(
        "Heatmap colors are field-adjusted for the number of finishing positions in each band."
    )
    if grouping == "variant":
        print(
            "Variant names use the archetype — variant display convention."
        )
    print()

    print(
        chart_data[
            [
                "Display_Name",
                "Players",
                "Average_Finish",
                "Median_Finish",
            ]
        ].to_string(
            index=False,
            formatters={
                "Average_Finish": "{:.1f}".format,
                "Median_Finish": "{:.1f}".format,
            },
        )
    )

    fig = draw_finish_distribution(
        distribution_data,
        tournament_name,
        total_players,
        number_of_groups,
        grouping,
    )

    output_path = save_chart(
        fig,
        "average_finish.png",
    )

    print(f"\nChart saved to:\n{output_path}")

    plt.show()


if __name__ == "__main__":
    main()