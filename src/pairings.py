"""
RK9 pairing retrieval, parsing, and player-resolution helpers.

RK9 does not expose a stable player identifier in its public pairing HTML.
This module therefore preserves the raw pairing identity and resolves it to
the existing deck-based ``player_key`` only when the roster match is unique.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, Tag

from src.config import BASE_URL, HEADERS


@dataclass(frozen=True)
class PairingPlayer:
    """One player as displayed in an RK9 pairing record."""

    first_name: str
    last_name: str
    country: str | None
    record: tuple[int, int, int] | None
    points: int | None
    outcome: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass(frozen=True)
class PairingMatch:
    """One RK9 round pairing, including byes and incomplete tables."""

    tournament_id: str
    division: str
    pod: int
    round_number: int
    table_number: int | None
    match_index: int
    player1: PairingPlayer | None
    player2: PairingPlayer | None
    status: str

    @property
    def match_key(self) -> str:
        table = "bye" if self.table_number is None else str(self.table_number)
        return ":".join(
            (
                self.tournament_id,
                str(self.pod),
                str(self.round_number),
                table,
                str(self.match_index),
            )
        )


@dataclass(frozen=True)
class ResolvedPlayer:
    """Resolution result for a raw pairing name."""

    player_key: str | None
    status: str
    candidates: tuple[str, ...]


def fetch_pairings_page(tournament_id: str) -> BeautifulSoup:
    """Fetch the RK9 pairing page containing division and round tabs."""

    url = f"{BASE_URL}/pairings/{tournament_id}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def fetch_round_fragment(
    tournament_id: str,
    pod: int,
    round_number: int,
) -> BeautifulSoup:
    """Fetch one RK9 HTMX round fragment."""

    url = f"{BASE_URL}/pairings/{tournament_id}"
    response = requests.get(
        url,
        params={"pod": pod, "rnd": round_number},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def get_division_rounds(soup: BeautifulSoup) -> dict[str, tuple[int, tuple[int, ...]]]:
    """
    Return ``division -> (pod, rounds)`` from an RK9 pairing page.

    The division tabs are the source of truth for the pod code. Round tabs
    are scoped by the same pod prefix, so this works across Masters, Senior,
    Junior, and future divisions without hard-coded pod values.
    """

    divisions: dict[str, tuple[int, tuple[int, ...]]] = {}

    for tab in soup.select('a[role="tab"][id$="-tab"]'):
        tab_id = tab.get("id", "")
        match = re.fullmatch(r"P(\d+)-tab", tab_id)
        if match is None:
            continue

        pod = int(match.group(1))
        text = tab.get_text(" ", strip=True)
        division = re.sub(r"\s+in Round \d+", "", text).strip()
        rounds = []

        for round_tab in soup.select(f'a[role="tab"][id^="P{pod}R"]'):
            round_match = re.fullmatch(
                rf"P{pod}R(\d+)-tab", round_tab.get("id", "")
            )
            if round_match is not None:
                rounds.append(int(round_match.group(1)))

        if rounds:
            divisions[division] = (pod, tuple(sorted(set(rounds))))

    return divisions


def _parse_record(cell: Tag) -> tuple[int, int, int] | None:
    record = cell.select_one(".record")
    if record is not None:
        values = [
            record.get("data-wins"),
            record.get("data-losses"),
            record.get("data-ties"),
        ]
        if all(value is not None for value in values):
            return tuple(int(value) for value in values)  # type: ignore[arg-type]

    match = re.search(r"\((\d+)-(\d+)-(\d+)\)", cell.get_text(" ", strip=True))
    return tuple(int(value) for value in match.groups()) if match else None


def _parse_player_cell(cell: Tag | None) -> PairingPlayer | None:
    if cell is None:
        return None

    name = cell.select_one(".name")
    if name is None:
        return None

    lines = [line.strip() for line in name.stripped_strings if line.strip()]
    if not lines:
        return None

    first_name = lines[0]
    last_line = lines[1] if len(lines) > 1 else ""
    country_match = re.search(r"\s*\[([^]]+)\]\s*$", last_line)
    country = country_match.group(1) if country_match else None
    last_name = re.sub(r"\s*\[[^]]+\]\s*$", "", last_line).strip()
    classes = set(cell.get("class", []))

    if "winner" in classes:
        outcome = "win"
    elif "loser" in classes:
        outcome = "loss"
    else:
        outcome = "tie_or_unknown"

    points_match = re.search(r"\b(\d+)\s+pts\b", cell.get_text(" ", strip=True))
    points = int(points_match.group(1)) if points_match else None

    return PairingPlayer(
        first_name=first_name,
        last_name=last_name,
        country=country,
        record=_parse_record(cell),
        points=points,
        outcome=outcome,
    )


def parse_round_fragment(
    soup: BeautifulSoup,
    tournament_id: str,
    division: str,
    pod: int,
    round_number: int,
) -> list[PairingMatch]:
    """Parse all matches from one RK9 round fragment."""

    matches = []
    for index, row in enumerate(soup.select("div.row.match")):
        player_cells = row.select(".player")
        player1 = _parse_player_cell(player_cells[0] if player_cells else None)
        player2 = _parse_player_cell(player_cells[1] if len(player_cells) > 1 else None)
        table = row.select_one(".tablenumber")
        table_text = table.get_text(" ", strip=True) if table else ""
        table_match = re.search(r"\d+", table_text)
        table_number = int(table_match.group()) if table_match else None

        if player1 is None and player2 is None:
            status = "empty"
        elif player1 is None or player2 is None:
            status = "bye_or_incomplete"
        elif "complete" in row.get("class", []) or any(
            outcome in {player.outcome for player in (player1, player2) if player}
            for outcome in ("win", "loss")
        ):
            status = "complete"
        else:
            status = "tie_or_incomplete"

        matches.append(
            PairingMatch(
                tournament_id=tournament_id,
                division=division,
                pod=pod,
                round_number=round_number,
                table_number=table_number,
                match_index=index,
                player1=player1,
                player2=player2,
                status=status,
            )
        )

    return matches


def scrape_tournament_pairings(tournament_id: str) -> list[PairingMatch]:
    """Download and parse every published RK9 pairing round."""

    page = fetch_pairings_page(tournament_id)
    matches = []
    for division, (pod, rounds) in get_division_rounds(page).items():
        for round_number in rounds:
            fragment = fetch_round_fragment(tournament_id, pod, round_number)
            matches.extend(
                parse_round_fragment(
                    fragment,
                    tournament_id,
                    division,
                    pod,
                    round_number,
                )
            )
    return matches


def normalize_player_name(first_name: str, last_name: str) -> str:
    """Normalize names for comparison without changing stored raw values."""

    value = f"{first_name} {last_name}"
    value = unicodedata.normalize("NFKC", value)
    value = value.casefold().replace("’", "'")
    return " ".join(value.split())


def resolve_player(
    pairing_player: PairingPlayer,
    roster_rows: list[dict[str, str]],
) -> ResolvedPlayer:
    """Resolve a pairing player against roster rows without guessing."""

    target_name = normalize_player_name(
        pairing_player.first_name,
        pairing_player.last_name,
    )
    candidates = [
        row
        for row in roster_rows
        if normalize_player_name(row["first_name"], row["last_name"]) == target_name
        and (
            pairing_player.country is None
            or row["country"].casefold() == pairing_player.country.casefold()
        )
    ]

    keys = tuple(row["player_key"] for row in candidates)
    if len(keys) == 1:
        return ResolvedPlayer(keys[0], "exact", keys)
    if len(keys) > 1:
        return ResolvedPlayer(None, "ambiguous", keys)
    return ResolvedPlayer(None, "unmatched", ())
