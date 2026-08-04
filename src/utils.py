"""
Utility functions used throughout the project.
"""


def create_player_key(deck_url):
    """
    Create a unique player identifier from an RK9 deck URL.

    Example
    -------
    https://rk9.gg/decklist/public/TU01w1D52rjGebrE8szS/01YEeCFeoPuPAcJYyfRP

    becomes

    01YEeCFeoPuPAcJYyfRP
    """

    return deck_url.rstrip("/").split("/")[-1]