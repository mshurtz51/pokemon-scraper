"""
Tech Card Performance visualization.

Ranks cards by the difference between Performance Index for selected decks
that include the card and selected decks that do not. Calculations match the
existing tech_card_performance analytics report and use Masters results only.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analytics_queries import (
    get_archetype_card_performance,
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

CUTS = {
    "Top 64": 64,
    "Top 128": 128,
    "Top 512": 512,
}


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


def select_group(df):
    """Prompt for an overall archetype and optional variant."""
    archetypes = sorted(df["overall"].dropna().unique())
    print("\nAvailable Archetypes:\n")
    for index, archetype in enumerate(archetypes, start=1):
        print(f"{index}. {archetype}")

    while True:
        try:
            choice = int(input("\nSelect archetype: "))
            if 1 <= choice <= len(archetypes):
                archetype = archetypes[choice - 1]
                break
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(archetypes)}.")

    selected = df[df["overall"] == archetype].copy()
    variants = sorted(selected["variant"].dropna().unique())
    print("\nSelect deck grouping:\n")
    print("1. Overall Archetype")
    print("2. Variant")
    while True:
        try:
            grouping_choice = int(input("\nSelect grouping: "))
            if grouping_choice in (1, 2):
                break
        except ValueError:
            pass
        print("Please enter 1 or 2.")

    if grouping_choice == 1:
        return selected, archetype, None

    print("\nAvailable Variants:\n")
    for index, variant in enumerate(variants, start=1):
        print(f"{index}. {variant}")
    while True:
        try:
            choice = int(input("\nSelect variant: "))
            if 1 <= choice <= len(variants):
                variant = variants[choice - 1]
                return selected[selected["variant"] == variant].copy(), archetype, variant
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(variants)}.")


def select_cut():
    """Prompt for cumulative or actual Performance Index cut."""
    print("\nPerformance Index cut:\n")
    for index, label in enumerate(CUTS, start=1):
        print(f"{index}. {label}")
    while True:
        try:
            choice = int(input("\nSelect cut: "))
            if 1 <= choice <= len(CUTS):
                return list(CUTS.values())[choice - 1], list(CUTS)[choice - 1]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(CUTS)}.")


def select_mode():
    """Prompt for Actual or Cumulative PI."""
    print("\nPerformance Index mode:\n")
    print("1. Actual: compare the selected finish band")
    print("2. Cumulative: compare all finishes through the cut")
    while True:
        try:
            choice = int(input("\nSelect mode: "))
            if choice in (1, 2):
                return choice == 2
        except ValueError:
            pass
        print("Please enter 1 or 2.")


def select_minimum_inclusion():
    """Prompt for a minimum card inclusion percentage."""
    print("\nMinimum card inclusion:\n")
    print("1. 0%")
    print("2. 5%")
    print("3. 10%")
    print("4. 20%")
    print("5. Custom")
    while True:
        try:
            choice = int(input("\nSelect minimum: "))
            if choice in (1, 2, 3, 4):
                return [0, 5, 10, 20][choice - 1]
            if choice == 5:
                return float(input("Minimum inclusion (%): "))
        except ValueError:
            pass
        print("Please enter a valid inclusion option.")


def select_include_core():
    """Prompt whether 99%+ cards should remain in the report."""
    print("\nInclude core cards (99%+ inclusion)?\n")
    print("1. Yes")
    print("2. No")
    while True:
        try:
            choice = int(input("\nSelect: "))
            if choice in (1, 2):
                return choice == 1
        except ValueError:
            pass
        print("Please enter 1 or 2.")


def select_display_count(max_count):
    """Prompt for the number of cards to display; zero means all."""
    print("\nHow many cards should be displayed?\n")
    print("0. All cards")
    while True:
        try:
            choice = int(input(f"\nSelect 0-{max_count}: "))
            if 0 <= choice <= max_count:
                return None if choice == 0 else choice
        except ValueError:
            pass
        print(f"Please enter a whole number from 0 to {max_count}.")


def _performance_index(frame, total_players, cut, cumulative):
    """Calculate PI for a subset using the established analytics definition."""
    players = frame["player_key"].nunique()
    if not players or not total_players:
        return 0.0

    if cumulative:
        top_players = frame[frame["standing"] <= cut]["player_key"].nunique()
        denominator = cut
    else:
        previous = {64: 32, 128: 64, 512: 256}[cut]
        top_players = frame[
            (frame["standing"] > previous) & (frame["standing"] <= cut)
        ]["player_key"].nunique()
        denominator = cut - previous

    expected = players / total_players * denominator
    return top_players / expected if expected else 0.0


def build_report(df, cut=64, cumulative=False, minimum_inclusion=0, include_core=True):
    """Build card inclusion and with/without-card PI comparisons."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["standing"] = pd.to_numeric(df["standing"], errors="coerce")
    df = df.dropna(subset=["player_key", "standing", "card_name"])
    total_players = df["player_key"].nunique()
    if not total_players:
        return pd.DataFrame()

    player_cards = df[["player_key", "card_name"]].drop_duplicates()
    all_players = set(df["player_key"])
    rows = []

    for card in sorted(player_cards["card_name"].unique()):
        with_players = set(
            player_cards.loc[player_cards["card_name"] == card, "player_key"]
        )
        without_players = all_players - with_players
        with_df = df[df["player_key"].isin(with_players)]
        without_df = df[df["player_key"].isin(without_players)]
        inclusion = len(with_players) / total_players * 100
        if inclusion < minimum_inclusion or (not include_core and inclusion >= 99):
            continue

        with_pi = _performance_index(with_df, total_players, cut, cumulative)
        without_pi = _performance_index(without_df, total_players, cut, cumulative)
        rows.append(
            {
                "Card": card,
                "Decks": len(with_players),
                "Inclusion": inclusion,
                "With PI": with_pi,
                "Without PI": without_pi,
                "Delta": with_pi - without_pi,
            }
        )

    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values(["Delta", "Inclusion", "Card"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


def _delta_color(value):
    if value > 0.05:
        return "#2F7D4A"
    if value < -0.05:
        return BRAND_COLOR
    return "#8A741C"


def _display_group(archetype, variant):
    if variant in (None, "", "Default"):
        return archetype
    return f"{archetype} — {variant}"


def create_chart(report, tournament_name, group_name, total_decks, cut_label, cumulative):
    """Create the ranked with/without-card comparison table."""
    row_count = len(report)
    figure_height = max(9.0, 4.4 + row_count * 0.34)
    fig = plt.figure(figsize=(16, figure_height), dpi=300)
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    fig.patch.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.text(0.05, 0.965, "Tech Card Performance", fontsize=25, fontweight="bold",
             color=TEXT_COLOR, ha="left", va="top")
    mode = "Cumulative" if cumulative else "Actual"
    fig.text(
        0.05, 0.928,
        f"{tournament_name}  •  {group_name}  •  {total_decks} Masters decklists  •  {mode} {cut_label}",
        fontsize=13, color=SECONDARY_TEXT_COLOR, ha="left", va="top",
    )
    fig.text(0.95, 0.965, "PTCG Data Viz", fontsize=18, fontweight="bold",
             color=BRAND_DARK, ha="right", va="top")

    left, right = 0.05, 0.95
    top, bottom = 0.865, 0.13
    widths = [0.28, 0.13, 0.15, 0.15, 0.15, 0.14]
    headers = ["Card", "Included", "Inclusion", "With card PI", "Without card PI", "Delta"]
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

    fig._tech_header = (left, top - row_height, right, top, BRAND_DARK)
    fig._tech_lines = []
    for row_index, (_, row) in enumerate(report.iterrows()):
        y = top - (row_index + 1.5) * row_height
        values = [
            row["Card"],
            f"{int(row['Decks'])}",
            f"{row['Inclusion']:.2f}%",
            f"{row['With PI']:.2f}x",
            f"{row['Without PI']:.2f}x",
            f"{row['Delta']:+.2f}x",
        ]
        colors = [TEXT_COLOR, TEXT_COLOR, TEXT_COLOR, TEXT_COLOR, TEXT_COLOR, _delta_color(row["Delta"])]
        for index, value in enumerate(values):
            x = x_positions[index]
            width = table_width * widths[index]
            fig.text(x + width / 2, y, str(value), fontsize=8.5,
                     fontweight="bold" if index in (0, 5) else "normal",
                     color=colors[index], ha="center", va="center")
        fig._tech_lines.append((left, y - row_height / 2, right, y - row_height / 2))

    fig.text(left, 0.08,
             "Delta compares Performance Index for decks including the card against decks without it.",
             fontsize=9, color=SECONDARY_TEXT_COLOR, ha="left", va="bottom")
    fig.text(left, 0.05,
             "+ = stronger representation among the selected finish range  •  − = weaker representation",
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

    left, bottom, right, top, color = fig._tech_header
    draw.line([point(left, bottom), point(right, bottom)], fill=color, width=max(2, int(width / 700)))
    draw.line([point(left, top), point(right, top)], fill=color, width=max(2, int(width / 700)))
    for x1, y1, x2, y2 in fig._tech_lines:
        draw.line([point(x1, y1), point(x2, y2)], fill=BORDER_COLOR, width=max(1, int(width / 1800)))
    image.save(output_path)


def main():
    tournament_id, tournament_name = select_tournament()
    all_cards = get_archetype_card_performance(tournament_id)
    selected, archetype, variant = select_group(all_cards)
    cut, cut_label = select_cut()
    cumulative = select_mode()
    minimum_inclusion = select_minimum_inclusion()
    include_core = select_include_core()

    report = build_report(
        selected,
        cut=cut,
        cumulative=cumulative,
        minimum_inclusion=minimum_inclusion,
        include_core=include_core,
    )
    if report.empty:
        print("No card performance data found for the selected group.")
        return

    display_count = select_display_count(len(report))
    if display_count is not None:
        report = report.head(display_count).copy()

    group_name = _display_group(archetype, variant)
    total_decks = selected["player_key"].nunique()
    print(f"\n{group_name}: {len(report)} cards across {total_decks} Masters decklists")
    print(report.to_string(index=False))

    fig = create_chart(report, tournament_name, group_name, total_decks, cut_label, cumulative)
    output_path = save_chart(
        fig,
        "tech_card_performance.png",
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
