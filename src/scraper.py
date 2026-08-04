"""
High-level tournament scraping functions.
"""

from src.deck import parse_deck


def parse_all_decks(players, decks):
    """
    Parse every deck in a tournament.

    Parameters
    ----------
    players : list[Player]
    decks : list[Deck]

    Returns
    -------
    list[DeckCard]
    """

    all_cards = []

    for player, deck in zip(players, decks):

        cards = parse_deck(
            deck.deck_url,
            player.player_key,
        )

        all_cards.extend(cards)

    return all_cards