"""SQLite persistence for raw RK9 pairing data."""

from __future__ import annotations

import json
import sqlite3

from src.config import PAIRING_DATABASE_NAME
from src.pairings import PairingMatch, PairingPlayer, ResolvedPlayer


def get_pairing_connection() -> sqlite3.Connection:
    """Return a connection to the separate pairing database."""

    return sqlite3.connect(str(PAIRING_DATABASE_NAME))


def create_pairing_database() -> None:
    """Create the pairing schema if it does not already exist."""

    conn = get_pairing_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pairing_matches (
            match_key TEXT PRIMARY KEY,
            tournament_id TEXT NOT NULL,
            division TEXT NOT NULL,
            pod INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            table_number INTEGER,
            match_index INTEGER NOT NULL,
            status TEXT NOT NULL,
            player1_first_name TEXT,
            player1_last_name TEXT,
            player1_country TEXT,
            player1_record TEXT,
            player1_points INTEGER,
            player1_outcome TEXT,
            player1_key TEXT,
            player1_resolution TEXT,
            player1_candidates TEXT,
            player1_day_2_contention INTEGER,
            player1_day_2 INTEGER,
            player2_first_name TEXT,
            player2_last_name TEXT,
            player2_country TEXT,
            player2_record TEXT,
            player2_points INTEGER,
            player2_outcome TEXT,
            player2_key TEXT,
            player2_resolution TEXT,
            player2_candidates TEXT,
            player2_day_2_contention INTEGER,
            player2_day_2 INTEGER
        )
        """
    )
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(pairing_matches)")
    }
    for column in (
        "player1_day_2_contention",
        "player1_day_2",
        "player2_day_2_contention",
        "player2_day_2",
    ):
        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE pairing_matches ADD COLUMN {column} INTEGER"
            )
    conn.commit()
    conn.close()


def tournament_pairings_exist(tournament_id: str) -> bool:
    """Return whether at least one pairing row is stored for a tournament."""

    conn = get_pairing_connection()
    row = conn.execute(
        "SELECT 1 FROM pairing_matches WHERE tournament_id = ? LIMIT 1",
        (tournament_id,),
    ).fetchone()
    conn.close()
    return row is not None


def _player_values(
    player: PairingPlayer | None,
    resolution: ResolvedPlayer | None,
) -> tuple[object, ...]:
    if player is None:
        return (None,) * 9

    return (
        player.first_name,
        player.last_name,
        player.country,
        json.dumps(player.record) if player.record else None,
        player.points,
        player.outcome,
        resolution.player_key if resolution else None,
        resolution.status if resolution else "unresolved",
    ) + (json.dumps(resolution.candidates) if resolution else "[]",)


def insert_pairing_matches(
    matches: list[PairingMatch],
    resolutions: dict[tuple[str, str], ResolvedPlayer] | None = None,
) -> None:
    """Insert or replace parsed matches while retaining raw identities."""

    resolutions = resolutions or {}
    rows = []
    for match in matches:
        p1_resolution = (
            resolutions.get((match.match_key, "player1"))
            if match.player1
            else None
        )
        p2_resolution = (
            resolutions.get((match.match_key, "player2"))
            if match.player2
            else None
        )
        rows.append(
            (
                match.match_key,
                match.tournament_id,
                match.division,
                match.pod,
                match.round_number,
                match.table_number,
                match.match_index,
                match.status,
                *_player_values(match.player1, p1_resolution),
                None,
                None,
                *_player_values(match.player2, p2_resolution),
                None,
                None,
            )
        )

    conn = get_pairing_connection()
    conn.executemany(
        """
        INSERT OR REPLACE INTO pairing_matches (
            match_key, tournament_id, division, pod, round_number,
            table_number, match_index, status,
            player1_first_name, player1_last_name, player1_country,
            player1_record, player1_points, player1_outcome, player1_key,
            player1_resolution, player1_candidates,
            player1_day_2_contention, player1_day_2,
            player2_first_name, player2_last_name, player2_country,
            player2_record, player2_points, player2_outcome, player2_key,
            player2_resolution, player2_candidates,
            player2_day_2_contention, player2_day_2
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()
