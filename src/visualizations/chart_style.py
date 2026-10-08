"""
Shared styling and helper functions for visualization scripts.
"""

from pathlib import Path

import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# Chart dimensions
# ---------------------------------------------------------------------

FIGURE_SIZE = (16, 9)
DPI = 300


# ---------------------------------------------------------------------
# PTCG Data Viz brand palette
# ---------------------------------------------------------------------

BACKGROUND_COLOR = "#FFFFFF"

BRAND_COLOR = "#A6192E"
BRAND_DARK = "#751324"

TEXT_COLOR = "#1A1A1A"
SECONDARY_TEXT_COLOR = "#6B6B6B"

GRID_COLOR = "#E6E6E6"
BORDER_COLOR = "#D4D4D4"


# ---------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------

TITLE_SIZE = 25
SUBTITLE_SIZE = 13

LABEL_SIZE = 11
TICK_SIZE = 10

OVERVIEW_TITLE_SIZE = 10
OVERVIEW_LABEL_SIZE = 10
OVERVIEW_VALUE_SIZE = 17

FOOTER_SIZE = 18


# ---------------------------------------------------------------------
# Chart setup
# ---------------------------------------------------------------------

def setup_chart(
    title=None,
    subtitle=None,
):
    """
    Create a consistently styled chart.

    Parameters
    ----------
    title : str, optional
        Main chart title.

    subtitle : str, optional
        Supporting description.

    Returns
    -------
    fig, ax
        Matplotlib figure and axes.
    """

    fig, ax = plt.subplots(
        figsize=FIGURE_SIZE,
        dpi=DPI,
    )

    fig.patch.set_facecolor(
        BACKGROUND_COLOR
    )

    ax.set_facecolor(
        BACKGROUND_COLOR
    )

    if title:

        fig.text(
            0.06,
            0.93,
            title,
            fontsize=TITLE_SIZE,
            fontweight="bold",
            color=TEXT_COLOR,
            ha="left",
            va="top",
        )

    if subtitle:

        fig.text(
            0.06,
            0.885,
            subtitle,
            fontsize=SUBTITLE_SIZE,
            color=SECONDARY_TEXT_COLOR,
            ha="left",
            va="top",
        )

    return fig, ax


# ---------------------------------------------------------------------
# Axes styling
# ---------------------------------------------------------------------

def style_axes(
    ax,
    show_x_grid=True,
    show_y_grid=False,
):
    """
    Apply consistent styling to chart axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Chart axes.

    show_x_grid : bool
        Whether to display vertical gridlines.

    show_y_grid : bool
        Whether to display horizontal gridlines.
    """

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.spines["bottom"].set_color(
        BORDER_COLOR
    )

    ax.tick_params(
        axis="both",
        colors=SECONDARY_TEXT_COLOR,
        labelsize=TICK_SIZE,
        length=0,
    )

    if show_x_grid:

        ax.grid(
            axis="x",
            color=GRID_COLOR,
            linewidth=0.8,
        )

    if show_y_grid:

        ax.grid(
            axis="y",
            color=GRID_COLOR,
            linewidth=0.8,
        )

    ax.set_axisbelow(True)


# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------

def add_footer(
    fig,
    text="PTCG Data Viz",
):
    """
    Add a consistent branded footer.
    """

    fig.text(
        0.015,
        0.015,
        text,
        fontsize=FOOTER_SIZE,
        fontweight="bold",
        color=BRAND_DARK,
        ha="left",
        va="bottom",
    )


# ---------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------

def save_chart(
    fig,
    filename,
    output_directory="output/visualizations",
    bbox_inches="tight",
    facecolor=None,
    opaque_background=False,
):
    """
    Save a chart using the project's standard export settings.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save.

    filename : str
        Output filename.

    output_directory : str or Path
        Directory where the chart will be saved.

    bbox_inches : str or None
        Bounding-box mode passed to Matplotlib. Use ``None`` for charts
        whose figure-level layout should be preserved without tight-bound
        transform calculations.

    facecolor : str or None
        Optional export background color. Defaults to the figure facecolor.

    opaque_background : bool
        Composite the saved image onto the export background so the PNG has
        no transparent pixels.

    Returns
    -------
    Path
        Path to the saved chart.
    """

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory / filename
    )

    fig.savefig(
        output_path,
        dpi=DPI,
        bbox_inches=bbox_inches,
        facecolor=(
            fig.get_facecolor()
            if facecolor is None
            else facecolor
        ),
    )

    if opaque_background:
        from PIL import Image

        background_color = (
            fig.get_facecolor()
            if facecolor is None
            else facecolor
        )
        image = Image.open(output_path).convert("RGBA")
        background = Image.new(
            "RGBA",
            image.size,
            background_color,
        )
        background.alpha_composite(image)
        background.convert("RGB").save(output_path)

    return output_path
