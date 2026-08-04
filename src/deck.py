"""
Functions for downloading and parsing RK9 decklists.
"""

import requests
from bs4 import BeautifulSoup

from src.config import HEADERS
from src.models import DeckCard


def fetch_deck(deck_url):
    """
    Fetch a single RK9 decklist.
    """

    response = requests.get(
    deck_url,
    headers=HEADERS,
    timeout=30,
)

    response.raise_for_status()

    return BeautifulSoup(response.text, "lxml")


def parse_card(card_element, player_key):
    """
    Parse one card from an RK9 decklist.
    """

    quantity = int(card_element["data-quantity"])

    card_name = card_element["data-cardname"]

    card_type = card_element["data-cardtype"]

    set_code, card_number = card_element["data-setnum"].split("-")

    return DeckCard(
        player_key=player_key,
        quantity=quantity,
        card_name=card_name,
        card_type=card_type,
        set_code=set_code,
        card_number=card_number,
    )


def parse_deck(deck_url, player_key):
    """
    Parse a complete decklist into DeckCard objects.
    """

    soup = fetch_deck(deck_url)

    english = soup.find("div", id="lang-EN")

    if english is None:
        raise ValueError("English decklist not found.")

    card_elements = english.find_all(
        "li",
        attrs={"data-cardname": True},
    )

    cards = []

    for card_element in card_elements:

        card = parse_card(card_element, player_key)

        cards.append(card)

    return cards