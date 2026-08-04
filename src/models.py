from dataclasses import dataclass


@dataclass
class Player:
    """
    Represents one player in a tournament.
    """

    player_key: str

    tournament_id: str

    first_name: str
    last_name: str

    country: str
    division: str

    standing: int | None

    deck_url: str