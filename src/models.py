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


@dataclass
class DeckCard:
    """
    Represents one card in one player's deck.
    """

    player_key: str

    quantity: int

    card_name: str

    card_type: str

    set_code: str
    card_number: str


@dataclass
class RuleResult:
    """
    Result of evaluating one archetype rule.
    """

    card_name: str
    operator: str
    expected: int
    actual: int
    passed: bool


@dataclass
class ClassificationResult:
    """
    Result of classifying a deck.
    """

    overall: str
    variant: str

    matched: bool

    priority: int | None

    score: float

    rule_results: list[RuleResult]

    core_pokemon: list[str]

    core_trainers: list[str]