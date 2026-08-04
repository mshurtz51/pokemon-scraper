"""
Functions for downloading and parsing RK9 tournament rosters.
"""

import requests
from bs4 import BeautifulSoup

from src.config import ROSTER_URL, HEADERS
from src.models import Player, Deck
from src.utils import create_player_key


def fetch_roster(tournament_id):
    """
    Download the HTML for a tournament roster.
    """

    url = ROSTER_URL + tournament_id

    response = requests.get(url, headers=HEADERS)

    response.raise_for_status()

    return BeautifulSoup(response.text, "lxml")


def get_player_rows(soup):
    """
    Return all player rows from the roster table.
    """

    table = soup.find("table", id="dtLiveRoster")

    if table is None:
        raise ValueError("Could not find roster table.")

    tbody = table.find("tbody")

    return tbody.find_all("tr")


def parse_player(row, tournament_id):
    """
    Parse one player row.
    """

    columns = row.find_all("td")

    first_name = columns[1].get_text(strip=True)
    last_name = columns[2].get_text(strip=True)
    country = columns[3].get_text(strip=True)
    division = columns[4].get_text(strip=True)

    # Deck URL
    link = columns[5].find("a")

    deck_url = None

    if link is not None:
        deck_url = "https://rk9.gg" + link["href"]

    # NEW: player key comes from the deck URL
    player_key = create_player_key(deck_url)

    # Standing
    standing_text = columns[6].get_text(strip=True)

    standing = int(standing_text) if standing_text else None

    player = Player(
        player_key=player_key,
        tournament_id=tournament_id,
        first_name=first_name,
        last_name=last_name,
        country=country,
        division=division,
        standing=standing,
    )

    deck = Deck(
        player_key=player_key,
        deck_url=deck_url,
    )

    return player, deck


def parse_roster(tournament_id):
    """
    Parse an entire tournament roster.
    """

    soup = fetch_roster(tournament_id)

    rows = get_player_rows(soup)

    players = []
    decks = []

    for row in rows:

        player, deck = parse_player(row, tournament_id)

        players.append(player)
        decks.append(deck)

    return players, decks