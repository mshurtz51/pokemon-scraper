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


@dataclass
class Deck:
    """
    Represents one player's submitted deck.
    """

    player_key: str
    deck_url: str