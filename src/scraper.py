"""
High-level tournament scraping functions.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.deck import parse_deck


def parse_all_decks(
    players,
    decks,
    skip_player_keys=None,
    workers=6,
    batch_size=50,
    on_batch=None,
):
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

    skip_player_keys = skip_player_keys or set()
    targets = [
        (player, deck)
        for player, deck in zip(players, decks)
        if player.player_key not in skip_player_keys
    ]

    all_cards = []
    completed = 0
    total = len(targets)

    def parse_one(pair):
        player, deck = pair
        return parse_deck(deck.deck_url, player.player_key)

    if workers <= 1:
        parsed = ((index, parse_one(pair)) for index, pair in enumerate(targets))
    else:
        executor = ThreadPoolExecutor(max_workers=workers)
        futures = {
            executor.submit(parse_one, pair): index
            for index, pair in enumerate(targets)
        }
        parsed = ((futures[future], future.result()) for future in as_completed(futures))

    try:
        for _, cards in parsed:
            completed += 1
            print(f"Parsing deck {completed}/{total}")
            all_cards.extend(cards)

            if on_batch and len(all_cards) >= batch_size:
                on_batch(all_cards)
                all_cards = []
    finally:
        if workers > 1:
            executor.shutdown(wait=True)

    if on_batch:
        if all_cards:
            on_batch(all_cards)
        return []

    return all_cards
