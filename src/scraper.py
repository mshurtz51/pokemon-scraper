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

    total = len(decks)

    for i, (player, deck) in enumerate(zip(players, decks), start=1):

        print(f"Parsing deck {i}/{total}")

        cards = parse_deck(
            deck.deck_url,
            player.player_key,
        )

        all_cards.extend(cards)

    return all_cards