"""
Meta Share timeline visualization by tournament.

Displays selected tournament meta share as a heatmap-style table,
with a directional trend indicator for each archetype or variant.
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.analytics_queries import (
    get_tournaments,
    get_all_tournament_results,
)

from src.visualizations.chart_style import (
    setup_chart,
    save_chart,
    BRAND_COLOR,
    BRAND_DARK,
    TEXT_COLOR,
    SECONDARY_TEXT_COLOR,
    GRID_COLOR,
    BORDER_COLOR,
    BACKGROUND_COLOR,
)


def select_tournaments():
    """
    Let the user choose one or more tournaments.
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

    choices = input(
        "\nSelect tournaments (comma separated): "
    )

    indices = [
        int(x.strip()) - 1
        for x in choices.split(",")
    ]

    return tournaments.iloc[indices]


def select_level():
    """
    Select archetype or variant.
    """
    print()
    print("=" * 60)
    print("LEVEL")
    print("=" * 60)
    print("1. Archetype")
    print("2. Variant")

    choice = int(
        input("\nSelect: ")
    )

    if choice == 1:
        return "overall"

    return "variant"


def select_top_n(grouping, max_groups):
    """
    Select the number of groups to display.

    The prompt changes between archetypes and variants,
    matching the behavior of the completed meta_share.py
    visualization.
    """
    label = (
        "archetypes"
        if grouping == "overall"
        else "variants"
    )

    print()
    print("=" * 60)
    print("DISPLAY")
    print("=" * 60)

    print(
        f"Number of {label} available in the "
        f"selected tournaments: {max_groups}"
    )

    while True:
        try:
            number = int(
                input(
                    f"How many {label} would you "
                    f"like to display? "
                )
            )

            if 1 <= number <= max_groups:
                return number

            print(
                f"Please enter a number between "
                f"1 and {max_groups}."
            )

        except ValueError:
            print("Please enter a valid number.")


def build_report(tournaments, results, level):
    """
    Build the meta share timeline report.

    In Variant mode, use the same display-name convention as
    meta_share.py so each variant remains tied to its archetype:
        Dragapult — Straight
        Dragapult — Dusknoir
        Ogerpon — Teal

    ``Default`` variants display only the archetype name.
    """
    rows = []

    for _, tournament in tournaments.iterrows():

        tournament_df = results[
            results["tournament_id"]
            == tournament["tournament_id"]
        ]

        total_players = len(
            tournament_df
        )

        if total_players == 0:
            continue

        if level == "overall":

            groups = [
                (overall, overall)
                for overall in sorted(
                    tournament_df["overall"]
                    .dropna()
                    .unique()
                )
            ]

        else:

            groups = []

            variant_groups = (
                tournament_df[
                    ["overall", "variant"]
                ]
                .dropna(subset=["overall", "variant"])
                .drop_duplicates()
            )

            for _, variant_row in variant_groups.iterrows():

                overall = variant_row["overall"]
                variant = variant_row["variant"]

                if variant == "Default":
                    display_name = overall
                else:
                    display_name = (
                        f"{overall} — {variant}"
                    )

                groups.append(
                    (
                        (overall, variant),
                        display_name,
                    )
                )

            groups = sorted(
                groups,
                key=lambda item: item[1],
            )

        for group, display_name in groups:

            if level == "overall":

                deck_df = tournament_df[
                    tournament_df["overall"]
                    == group
                ]

            else:

                overall, variant = group

                deck_df = tournament_df[
                    (
                        tournament_df["overall"]
                        == overall
                    )
                    & (
                        tournament_df["variant"]
                        == variant
                    )
                ]

            players = len(deck_df)

            meta_share = (
                players
                / total_players
                * 100
            )

            rows.append(
                {
                    "Group": display_name,
                    "Tournament": tournament[
                        "tournament_name"
                    ],
                    "Meta Share": meta_share,
                    "Date": tournament[
                        "start_date"
                    ],
                }
            )

    return pd.DataFrame(rows)
def prepare_timeline(
    report,
    tournaments,
    top_n=None,
):
    """
    Prepare chronological tournament order and
    apply the Top-N display filter.
    """
    if report.empty:
        return report, []

    tournaments = tournaments.copy()

    tournaments["start_date"] = pd.to_datetime(
        tournaments["start_date"]
    )

    tournament_order = (
        tournaments.sort_values(
            "start_date"
        )["tournament_name"]
        .tolist()
    )

    report = report[
        report["Tournament"].isin(
            tournament_order
        )
    ].copy()

    rankings = (
        report.groupby("Group")["Meta Share"]
        .mean()
        .sort_values(
            ascending=False
        )
    )

    if top_n is not None:
        report = report[
            report["Group"].isin(
                rankings.head(top_n).index
            )
        ].copy()

    return (
        report,
        tournament_order,
    )


def calculate_trend(report, group):
    """
    Determine overall direction from the first
    selected tournament to the last selected tournament.

    A change of less than 0.5 percentage points is
    treated as neutral.
    """
    group_df = report[
        report["Group"] == group
    ].copy()

    if group_df.empty:
        return "NEUTRAL"

    group_df = group_df.sort_values(
        "Date"
    )

    first_value = group_df.iloc[0]["Meta Share"]
    last_value = group_df.iloc[-1]["Meta Share"]

    change = last_value - first_value

    if change >= 0.5:
        return "RISING"

    if change <= -0.5:
        return "FALLING"

    return "NEUTRAL"


def heatmap_color(value, column_min, column_max):
    """
    Return a green -> yellow -> red conditional-formatting color.

    The scale is calculated independently for each tournament
    column so each column shows its own relative meta-share
    distribution.

    Low values = red
    Middle values = yellow
    High values = green
    """
    if column_max <= column_min:
        normalized = 0.5
    else:
        normalized = (
            value - column_min
        ) / (
            column_max - column_min
        )

    normalized = max(
        0.0,
        min(
            1.0,
            normalized,
        ),
    )

    red = (194, 45, 45)
    yellow = (242, 210, 74)
    green = (70, 165, 80)

    if normalized < 0.5:
        position = normalized * 2

        rgb = tuple(
            int(
                red[index]
                + (
                    yellow[index]
                    - red[index]
                ) * position
            )
            for index in range(3)
        )

    else:
        position = (
            normalized - 0.5
        ) * 2

        rgb = tuple(
            int(
                yellow[index]
                + (
                    green[index]
                    - yellow[index]
                ) * position
            )
            for index in range(3)
        )

    # Soften the conditional-formatting colors.
    blend = 0.72

    rgb = tuple(
        int(
            channel
            + (255 - channel) * blend
        )
        for channel in rgb
    )

    return (
        f"#{rgb[0]:02X}"
        f"{rgb[1]:02X}"
        f"{rgb[2]:02X}"
    )


def draw_heatmap_table(
    report,
    tournament_order,
    level,
    top_n=None,
):
    """
    Draw the heatmap-style meta share table.
    """
    if report.empty:
        return None

    # Rank rows by the final tournament, matching the
    # existing console report's ordering philosophy.
    last_tournament = tournament_order[-1]

    final_rank = (
        report[
            report["Tournament"]
            == last_tournament
        ]
        .set_index("Group")["Meta Share"]
        .sort_values(
            ascending=False
        )
    )

    # Include groups that do not appear in the final
    # tournament at the bottom.
    all_groups = (
        report["Group"]
        .drop_duplicates()
        .tolist()
    )

    ordered_groups = (
        final_rank.index.tolist()
        + [
            group
            for group in all_groups
            if group not in final_rank.index
        ]
    )

    if level == "overall":
        title = "Archetype Meta Share Timeline"
    else:
        title = "Variant Meta Share Timeline"

    subtitle = "Meta share across selected tournaments"

    if top_n is not None:
        subtitle += f" | Top {top_n}"

    fig, ax = setup_chart(
        title=title,
        subtitle=subtitle,
    )

    ax.axis("off")

    # Keep the table centered in the main chart area.
    table_left = 0.055
    table_bottom = 0.105
    table_width = 0.89
    table_height = 0.70

    group_width = 0.25
    trend_width = 0.15

    tournament_count = len(
        tournament_order
    )

    remaining_width = (
        1
        - group_width
        - trend_width
    )

    tournament_width = (
        remaining_width
        / max(tournament_count, 1)
    )

    column_widths = (
        [group_width]
        + [tournament_width] * tournament_count
        + [trend_width]
    )

    row_count = len(ordered_groups)

    header_height = 0.085
    row_height = (
        table_height - header_height
    ) / max(row_count, 1)

    # Header background.
    x_cursor = table_left

    group_header = (
        "Archetype"
        if level == "overall"
        else "Archetype / Variant"
    )

    headers = (
        [group_header]
        + tournament_order
        + ["Trend"]
    )

    for index, header in enumerate(headers):
        width = column_widths[index]

        rect = Rectangle(
            (
                x_cursor,
                table_bottom
                + table_height
                - header_height,
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
            table_bottom
            + table_height
            - header_height / 2,
            header,
            fontsize=10,
            fontweight="bold",
            color="white",
            ha="center",
            va="center",
        )

        x_cursor += width

    # Data rows.
    # Normalize each tournament column independently.
    # This makes the heatmap answer "which archetypes were
    # relatively most represented at this tournament?" rather
    # than turning every cell into a similar shade of red.
    column_min = {}
    column_max = {}

    for tournament in tournament_order:
        values = report.loc[
            report["Tournament"] == tournament,
            "Meta Share",
        ]

        column_min[tournament] = (
            float(values.min())
            if not values.empty
            else 0
        )

        column_max[tournament] = (
            float(values.max())
            if not values.empty
            else 1
        )

    for row_index, group in enumerate(
        ordered_groups
    ):

        y = (
            table_bottom
            + table_height
            - header_height
            - (row_index + 1)
            * row_height
        )

        group_df = report[
            report["Group"] == group
        ]

        # Archetype name cell.
        rect = Rectangle(
            (
                table_left,
                y,
            ),
            group_width,
            row_height,
            transform=fig.transFigure,
            facecolor="#F7F7F5",
            edgecolor=BACKGROUND_COLOR,
            linewidth=1.5,
            zorder=1,
        )

        fig.add_artist(rect)

        fig.text(
            table_left + group_width / 2,
            y + row_height / 2,
            str(group),
            fontsize=10,
            color=TEXT_COLOR,
            ha="center",
            va="center",
        )

        # Tournament cells.
        for tournament_index, tournament in enumerate(
            tournament_order
        ):

            x = (
                table_left
                + group_width
                + tournament_index
                * tournament_width
            )

            match = group_df[
                group_df["Tournament"]
                == tournament
            ]

            value = (
                0
                if match.empty
                else match.iloc[0]["Meta Share"]
            )

            # Keep the heatmap subtle: the table should read
            # primarily as data, with color used as a secondary cue.
            # Conditional formatting is applied ONLY to
            # percentage cells, independently by tournament.
            cell_color = heatmap_color(
                value,
                column_min[tournament],
                column_max[tournament],
            )

            rect = Rectangle(
                (
                    x,
                    y,
                ),
                tournament_width,
                row_height,
                transform=fig.transFigure,
                facecolor=cell_color,
                edgecolor=BACKGROUND_COLOR,
                linewidth=1.5,
                zorder=1,
            )

            fig.add_artist(rect)

            text_color = TEXT_COLOR

            fig.text(
                x + tournament_width / 2,
                y + row_height / 2,
                f"{value:.1f}%",
                fontsize=10,
                fontweight="bold",
                color=text_color,
                ha="center",
                va="center",
            )

        # Trend cell.
        trend = calculate_trend(
            report,
            group,
        )

        trend_x = (
            table_left
            + group_width
            + tournament_count
            * tournament_width
        )

        trend_rect = Rectangle(
            (
                trend_x,
                y,
            ),
            trend_width,
            row_height,
            transform=fig.transFigure,
            facecolor="#F7F7F5",
            edgecolor=BACKGROUND_COLOR,
            linewidth=1.5,
            zorder=1,
        )

        fig.add_artist(trend_rect)

        trend_color = SECONDARY_TEXT_COLOR

        if trend == "RISING":
            trend_color = "#228B22"
        elif trend == "FALLING":
            trend_color = "#B22222"

        fig.text(
            trend_x + trend_width / 2,
            y + row_height / 2,
            trend,
            fontsize=9,
            fontweight="bold",
            color=trend_color,
            ha="center",
            va="center",
        )

    # Small explanatory note.
    fig.text(
        table_left,
        table_bottom - 0.035,
        "Trend compares meta share in the first and last selected tournaments; "
        "changes under 0.5 percentage points are neutral.",
        fontsize=9,
        color=SECONDARY_TEXT_COLOR,
        ha="left",
        va="top",
    )

    # Brand treatment.
    fig.text(
        0.94,
        0.93,
        "PTCG Data Viz",
        fontsize=18,
        fontweight="bold",
        color=BRAND_DARK,
        ha="right",
        va="top",
    )

    filename = (
        "meta_share_timeline.png"
        if level == "overall"
        else "variant_meta_share_timeline.png"
    )

    output_path = save_chart(
        fig,
        filename,
    )

    plt.show()

    return output_path


def main():
    tournaments = select_tournaments()

    if tournaments.empty:
        print(
            "No tournaments selected."
        )
        return

    level = select_level()

    results = get_all_tournament_results()

    # Build the selected-tournament report first. The available
    # group count must reflect only the tournaments the user chose,
    # not the entire database.
    report = build_report(
        tournaments,
        results,
        level,
    )

    if report.empty:
        print()
        print(
            "No data found for the selected tournaments."
        )
        return

    max_groups = (
        report["Group"]
        .dropna()
        .nunique()
    )

    top_n = select_top_n(
        level,
        max_groups,
    )

    report, tournament_order = (
        prepare_timeline(
            report,
            tournaments,
            top_n=top_n,
        )
    )

    draw_heatmap_table(
        report,
        tournament_order,
        level,
        top_n=top_n,
    )


if __name__ == "__main__":
    main()
