"""
Functions for reading metadata.xlsx.
"""

from pathlib import Path

import pandas as pd

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Metadata workbook
METADATA_FILE = PROJECT_ROOT / "metadata" / "metadata.xlsx"


def load_tournaments():
    """
    Load the tournaments worksheet.

    Returns
    -------
    pandas.DataFrame
    """

    return pd.read_excel(
        METADATA_FILE,
        sheet_name="tournaments",
    )


def load_sets():
    """
    Load the sets worksheet.

    Returns
    -------
    pandas.DataFrame
    """

    return pd.read_excel(
        METADATA_FILE,
        sheet_name="sets",
    )