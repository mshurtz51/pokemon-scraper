"""
Utility functions used throughout the project.
"""


def create_player_key(
    tournament_id: str,
    first_name: str,
    last_name: str,
    division: str,
) -> str:
    """
    Create a unique internal identifier for a player.
    """

    return (
        f"{tournament_id}|"
        f"{first_name}|"
        f"{last_name}|"
        f"{division}"
    )