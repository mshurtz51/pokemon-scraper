"""
Archetype Meta Share Visualization
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import FancyBboxPatch
import pandas as pd

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
    OVERVIEW_TITLE_SIZE,
    OVERVIEW_LABEL_SIZE,
    OVERVIEW_VALUE_SIZE,
    setup_chart,
    style_axes,
    add_footer,
    save_chart,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The metadata workbook may live either in the project root or in the
# metadata folder. The loader below also searches the metadata folder
# if neither standard location exists.
METADATA_CANDIDATES = [
    PROJECT_ROOT / "metadata.xlsx",
    PROJECT_ROOT / "metadata" / "metadata.xlsx",
]

SET_ASSET_FOLDER = PROJECT_ROOT / "assets" / "sets"


# ---------------------------------------------------------------------
# Tournament selection
# ---------------------------------------------------------------------

def select_tournament():
    """Display available tournaments and prompt the user to select one."""

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


# ---------------------------------------------------------------------
# Grouping selection
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# Number of groups to display
# ---------------------------------------------------------------------

def select_number_of_decks(max_groups, grouping):
    """Prompt the user to select how many groups should be displayed."""

    label = "archetypes" if grouping == "overall" else "variants"

    print(
        f"\nNumber of {label} available: "
        f"{max_groups}"
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


# ---------------------------------------------------------------------
# Meta share calculation
# ---------------------------------------------------------------------

def calculate_meta_share(df, grouping="overall"):
    """Calculate meta share."""

    if grouping == "overall":

        report = (
            df.groupby("overall")
            .size()
            .reset_index(name="players")
        )

        report["display_name"] = report["overall"]

    else:

        report = (
            df.groupby(
                [
                    "overall",
                    "variant",
                ]
            )
            .size()
            .reset_index(name="players")
        )

        report["display_name"] = (
            report["overall"]
            + report["variant"].apply(
                lambda x:
                ""
                if x == "Default"
                else f" — {x}"
            )
        )

    total_players = report["players"].sum()

    report["meta_share"] = (
        report["players"]
        / total_players
        * 100
    )

    return report


# ---------------------------------------------------------------------
# Tournament metadata
# ---------------------------------------------------------------------

def _find_column(df, name):
    """
    Find a metadata column case-insensitively.

    This lets the visualization work with the current metadata workbook
    even if column capitalization differs.
    """

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    return normalized.get(name.lower())


def _empty_tournament_context():
    """Return a blank tournament context."""

    return {
        "format": "",
        "event_type": "",
        "city": "",
        "state_province": "",
        "country": "",
        "start_date": "",
        "begin_set": "",
        "end_set": "",
        "notes": "",
        "sets": [],
    }


def _find_metadata_file():
    """Find the metadata workbook without assuming one exact location."""

    for path in METADATA_CANDIDATES:
        if path.exists():
            return path

    metadata_folder = PROJECT_ROOT / "metadata"

    if metadata_folder.exists():
        matches = sorted(metadata_folder.glob("*.xlsx"))
        if matches:
            return matches[0]

    return None


def _resolve_sheet_by_columns(workbook, required_columns):
    """Find a worksheet by the columns it contains, not by sheet name."""

    required = {column.strip().lower() for column in required_columns}

    for sheet_name in workbook.sheet_names:
        try:
            sample = pd.read_excel(
                workbook,
                sheet_name=sheet_name,
                nrows=0,
            )
        except Exception:
            continue

        columns = {
            str(column).strip().lower()
            for column in sample.columns
        }

        if required.issubset(columns):
            return sheet_name

    return None


def load_tournament_context(tournament_id):
    """
    Load tournament metadata and the set logos used by the tournament.

    Worksheet names are discovered from their column structure, so this
    does not depend on the workbook using the exact names ``Tournaments``
    and ``Sets``.
    """

    metadata_file = _find_metadata_file()

    if metadata_file is None:
        return _empty_tournament_context()

    try:
        workbook = pd.ExcelFile(metadata_file)
    except Exception:
        return _empty_tournament_context()

    tournament_sheet = _resolve_sheet_by_columns(
        workbook,
        ["tournament_id", "tournament_name"],
    )

    set_sheet = _resolve_sheet_by_columns(
        workbook,
        ["set_code"],
    )

    if tournament_sheet is None:
        return _empty_tournament_context()

    try:
        tournaments = pd.read_excel(
            workbook,
            sheet_name=tournament_sheet,
        )
    except Exception:
        return _empty_tournament_context()

    if set_sheet is not None:
        try:
            sets = pd.read_excel(
                workbook,
                sheet_name=set_sheet,
            )
        except Exception:
            sets = pd.DataFrame()
    else:
        sets = pd.DataFrame()

    tournament_id_col = _find_column(
        tournaments,
        "tournament_id",
    )

    if tournament_id_col is None:
        return _empty_tournament_context()

    tournament = tournaments[
        tournaments[tournament_id_col].astype(str).str.strip()
        == str(tournament_id).strip()
    ]

    if tournament.empty:
        return _empty_tournament_context()

    tournament = tournament.iloc[0]

    def value(name):
        column = _find_column(tournaments, name)

        if column is None:
            return ""

        result = tournament[column]

        if pd.isna(result):
            return ""

        return str(result).strip()

    begin_set = value("begin_set")
    end_set = value("end_set")

    set_code_col = _find_column(sets, "set_code")
    order_col = _find_column(sets, "order")
    asset_filename_col = _find_column(sets, "asset_filename")
    set_name_col = _find_column(sets, "set_name")

    tournament_sets = []

    if set_code_col is not None and begin_set and end_set:
        set_codes = sets[set_code_col].astype(str).str.strip()

        begin_matches = sets[
            set_codes.str.upper() == begin_set.upper()
        ]
        end_matches = sets[
            set_codes.str.upper() == end_set.upper()
        ]

        if not begin_matches.empty and not end_matches.empty:
            begin_row = begin_matches.iloc[0]
            end_row = end_matches.iloc[0]

            if order_col is not None:
                # Coerce the ordering column to numeric where possible.
                # This keeps the set sequence correct even if Excel stored
                # the values as text.
                ordered = sets.copy()
                ordered["__set_order_numeric"] = pd.to_numeric(
                    ordered[order_col],
                    errors="coerce",
                )

                begin_order = pd.to_numeric(
                    begin_row[order_col],
                    errors="coerce",
                )
                end_order = pd.to_numeric(
                    end_row[order_col],
                    errors="coerce",
                )

                if pd.notna(begin_order) and pd.notna(end_order):
                    selected_sets = ordered[
                        (ordered["__set_order_numeric"] >= begin_order)
                        & (ordered["__set_order_numeric"] <= end_order)
                    ].sort_values("__set_order_numeric")
                else:
                    selected_sets = pd.DataFrame([begin_row, end_row])
            else:
                selected_sets = pd.DataFrame([begin_row, end_row])

            selected_codes = set()

            for _, set_row in selected_sets.iterrows():
                set_code = str(set_row[set_code_col]).strip()

                if set_code.upper() in selected_codes:
                    continue

                selected_codes.add(set_code.upper())

                asset_filename = ""

                if asset_filename_col is not None:
                    raw_filename = set_row[asset_filename_col]
                    if pd.notna(raw_filename):
                        asset_filename = str(raw_filename).strip()

                asset_path = (
                    SET_ASSET_FOLDER / asset_filename
                    if asset_filename
                    else None
                )

                if set_name_col is not None and pd.notna(set_row[set_name_col]):
                    set_name = str(set_row[set_name_col]).strip()
                else:
                    set_name = set_code

                tournament_sets.append(
                    {
                        "set_code": set_code,
                        "set_name": set_name,
                        "asset_path": asset_path,
                    }
                )

    return {
        "format": value("format"),
        "event_type": value("event_type"),
        "city": value("city"),
        "state_province": value("state_province"),
        "country": value("country"),
        "start_date": value("start_date"),
        "begin_set": begin_set,
        "end_set": end_set,
        "notes": value("notes"),
        "sets": tournament_sets,
    }


# ---------------------------------------------------------------------
# Set logo rendering
# ---------------------------------------------------------------------

def draw_set_logos(info_ax, sets):
    """Draw only the first and last tournament set logos inside the info box."""

    available = [
        item
        for item in sets
        if item["asset_path"] is not None
        and item["asset_path"].exists()
    ]

    if not available:
        return False

    if len(available) == 1:
        display_sets = available
    else:
        display_sets = [available[0], available[-1]]

    positions = [
        (0.10, 0.35, 0.34, 0.13),
        (0.56, 0.35, 0.34, 0.13),
    ]

    for item, (x, y, width, height) in zip(display_sets, positions):
        try:
            image = mpimg.imread(item["asset_path"])
        except Exception:
            continue

        logo_ax = info_ax.inset_axes([x, y, width, height])
        logo_ax.imshow(image)
        logo_ax.axis("off")
        logo_ax.set_facecolor("none")

    return True


# ---------------------------------------------------------------------
# Chart creation
# ---------------------------------------------------------------------

def create_chart(
    report,
    tournament_id,
    tournament_name,
    number_of_decks,
    grouping,
    tournament_notes="",
):
    """Create the meta share chart."""

    chart_data = (
        report
        .sort_values(
            "meta_share",
            ascending=False,
        )
        .head(number_of_decks)
        .sort_values(
            "meta_share",
            ascending=True,
        )
    )

    total_players = int(
        report["players"].sum()
    )

    total_groups = len(report)

    displayed_meta_share = (
        chart_data["meta_share"].sum()
    )

    other_meta_share = max(
        0,
        100 - displayed_meta_share,
    )

    if grouping == "overall":
        grouping_text = "Variant Grouping Off"
        group_label = "Deck Archetypes"
        other_label = "Other Archetypes"
    else:
        grouping_text = "Variant Grouping On"
        group_label = "Total Deck Variants"
        other_label = "Other Variants"

    subtitle = (
        f"{tournament_name} | "
        f"Masters Division | "
        f"Top {number_of_decks} | "
        f"{grouping_text}"
    )

    fig, ax = setup_chart(
        title="Archetype Meta Share",
        subtitle=subtitle,
    )

    # Top-right brand mark.
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

    # -------------------------------------------------------------
    # Main chart area
    # -------------------------------------------------------------

    ax.set_position(
        [
            0.10,
            0.13,
            0.60,
            0.70,
        ]
    )

    bars = ax.barh(
        chart_data["display_name"],
        chart_data["meta_share"],
        color=BRAND_COLOR,
        height=0.72,
    )

    style_axes(
        ax,
        show_x_grid=False,
        show_y_grid=False,
    )

    ax.set_xlabel("")

    ax.tick_params(
        axis="x",
        which="both",
        bottom=False,
        labelbottom=False,
    )

    max_share = chart_data["meta_share"].max()

    ax.set_xlim(
        0,
        max_share * 1.18,
    )

    # -------------------------------------------------------------
    # Bar labels
    # -------------------------------------------------------------

    for bar, share, players in zip(
        bars,
        chart_data["meta_share"],
        chart_data["players"],
    ):
        # Bubble sits at the inside-left/base of the bar, directly beside
        # the archetype label. This remains consistent for every bar.
        bubble_x = share * 0.02

        ax.text(
            bubble_x,
            bar.get_y() + bar.get_height() / 2,
            f"{int(players):,} players",
            va="center",
            ha="left",
            fontsize=LABEL_SIZE,
            fontweight="bold",
            color=BACKGROUND_COLOR,
            bbox=dict(
                boxstyle="round,pad=0.28",
                facecolor=BRAND_COLOR,
                edgecolor=BACKGROUND_COLOR,
                linewidth=1.2,
            ),
        )

        ax.text(
            share + max_share * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{share:.1f}%",
            va="center",
            ha="left",
            fontsize=LABEL_SIZE,
            fontweight="bold",
            color=TEXT_COLOR,
        )

    # -------------------------------------------------------------
    # Tournament information box
    # -------------------------------------------------------------

    context = load_tournament_context(tournament_id)

    # The entire right rail is one real figure-level box.
    # All tournament information is rendered inside this container.
    box_left = 0.70
    box_bottom = 0.28
    box_width = 0.235
    box_height = 0.50

    box = FancyBboxPatch(
        (box_left, box_bottom),
        box_width,
        box_height,
        boxstyle="round,pad=0.004,rounding_size=0.004",
        transform=fig.transFigure,
        facecolor="#F5F5F2",
        edgecolor="none",
        linewidth=0,
        zorder=0,
    )
    fig.add_artist(box)

    # Transparent axes placed exactly over the box.
    info_ax = fig.add_axes(
        [box_left, box_bottom, box_width, box_height],
        facecolor="none",
        frameon=False,
        zorder=1,
    )
    info_ax.set_xlim(0, 1)
    info_ax.set_ylim(0, 1)
    info_ax.axis("off")

    section_left = 0.06
    section_right = 0.94

    def add_section_title(y, title):
        """Add a section title with enough clearance above its underline."""
        info_ax.text(
            section_left,
            y,
            title,
            fontsize=OVERVIEW_TITLE_SIZE,
            fontweight="bold",
            color=BRAND_DARK,
            ha="left",
            va="top",
        )

        info_ax.plot(
            [section_left, section_right],
            [y - 0.035, y - 0.035],
            color=BRAND_COLOR,
            linewidth=1.4,
            clip_on=False,
        )

    # -------------------------------------------------------------
    # Tournament overview
    # -------------------------------------------------------------

    add_section_title(.98, "TOURNAMENT OVERVIEW")

    info_ax.text(
        section_left, 0.90, f"{total_players:,}",
        fontsize=OVERVIEW_VALUE_SIZE, fontweight="bold",
        color=TEXT_COLOR, ha="left", va="top",
    )
    info_ax.text(
        section_left, 0.85, "Players",
        fontsize=OVERVIEW_LABEL_SIZE, color=SECONDARY_TEXT_COLOR,
        ha="left", va="top",
    )

    info_ax.text(
        0.54, 0.90, f"{total_groups:,}",
        fontsize=OVERVIEW_VALUE_SIZE, fontweight="bold",
        color=TEXT_COLOR, ha="left", va="top",
    )
    info_ax.text(
        0.54, 0.85, group_label,
        fontsize=OVERVIEW_LABEL_SIZE, color=SECONDARY_TEXT_COLOR,
        ha="left", va="top",
    )

    info_ax.text(
        section_left, 0.80, f"{other_meta_share:.1f}%",
        fontsize=OVERVIEW_VALUE_SIZE, fontweight="bold",
        color=BRAND_COLOR, ha="left", va="top",
    )
    info_ax.text(
        section_left, 0.75, other_label,
        fontsize=OVERVIEW_LABEL_SIZE, color=SECONDARY_TEXT_COLOR,
        ha="left", va="top",
    )

    # -------------------------------------------------------------
    # Tournament context
    # -------------------------------------------------------------

    add_section_title(0.70, "TOURNAMENT CONTEXT")

    event_type = context["event_type"]
    event_type_display = {
        "IC": "International Championship",
        "International Championship": "International Championship",
    }.get(event_type, event_type or "Not Available")

    format_value = context["format"] or "Not Available"

    info_ax.text(
        section_left, 0.62,
        f"Tournament Type: {event_type_display}",
        fontsize=OVERVIEW_LABEL_SIZE, color=TEXT_COLOR,
        ha="left", va="top",
    )
    info_ax.text(
        section_left, 0.57,
        f"Format: {format_value}",
        fontsize=OVERVIEW_LABEL_SIZE, color=TEXT_COLOR,
        ha="left", va="top",
    )

    info_ax.text(
        0.27, 0.525, "From:",
        fontsize=OVERVIEW_LABEL_SIZE, fontweight="bold",
        color=SECONDARY_TEXT_COLOR, ha="center", va="top",
    )
    info_ax.text(
        0.73, 0.525, "To:",
        fontsize=OVERVIEW_LABEL_SIZE, fontweight="bold",
        color=SECONDARY_TEXT_COLOR, ha="center", va="top",
    )

    # Logos sit directly below the From/To labels, leaving room for notes below.
    logos_drawn = draw_set_logos(info_ax, context["sets"])

    if not logos_drawn and context["begin_set"] and context["end_set"]:
        info_ax.text(
            0.55, 0.50,
            f"{context['begin_set']} — {context['end_set']}",
            fontsize=OVERVIEW_LABEL_SIZE, color=SECONDARY_TEXT_COLOR,
            ha="center", va="top",
        )

    # -------------------------------------------------------------
    # Tournament notes
    # -------------------------------------------------------------

    add_section_title(0.33, "TOURNAMENT NOTES")

    notes = tournament_notes.strip()
    if not notes:
        notes = "No tournament notes available."

    info_ax.text(
        section_left, 0.25, notes,
        fontsize=OVERVIEW_LABEL_SIZE, color=SECONDARY_TEXT_COLOR,
        style="italic", ha="left", va="top",
        wrap=True, linespacing=1.2,
    )

    return fig


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    """Run the visualization."""

    tournament_id, tournament_name = (
        select_tournament()
    )

    df = get_tournament_results(
        tournament_id
    )

    if df.empty:
        print("\nNo tournament data found.")
        return

    grouping = select_grouping()

    report = calculate_meta_share(
        df,
        grouping=grouping,
    )

    number_of_decks = select_number_of_decks(
        len(report),
        grouping,
    )

    display_report = (
        report
        .sort_values(
            "meta_share",
            ascending=False,
        )
        .head(number_of_decks)
    )

    print("\nMeta Share:")

    print(
        display_report[
            [
                "display_name",
                "players",
                "meta_share",
            ]
        ].to_string(
            index=False,
            formatters={
                "meta_share": "{:.1f}%".format
            },
        )
    )

    # Prompt for notes every time the visualization is generated.
    print("\nTournament Notes")
    tournament_notes = input(
        "Enter notes for this tournament (press Enter to leave blank): "
    ).strip()

    fig = create_chart(
        report,
        tournament_id,
        tournament_name,
        number_of_decks,
        grouping,
        tournament_notes=tournament_notes,
    )

    output_path = save_chart(
        fig,
        "archetype_meta_share.png",
    )

    print(
        f"\nChart saved to:\n{output_path}"
    )

    plt.show()


if __name__ == "__main__":
    main()
