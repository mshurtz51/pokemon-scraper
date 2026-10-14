"""Build and summarize matchup records from RK9 pairings and deck data."""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.config import DATABASE_NAME, PAIRING_DATABASE_NAME
from src.pairing_database import create_pairing_database


MATCHUP_COLUMNS = (
    "match_key, tournament_id, division, pod, round_number, table_number, "
    "status, player1_key, player2_key, player1_deck_url, player2_deck_url, "
    "player1_outcome, player2_outcome, player1_record, player2_record, "
    "player1_points_after, player2_points_after, player1_points_before, "
    "player2_points_before, player1_overall, player1_variant, player2_overall, "
    "player2_variant, player1_day_2_contention, player1_day_2, "
    "player2_day_2_contention, player2_day_2, match_result, "
    "eligible_for_analytics"
)

SOURCE_COLUMNS = """
    m.match_key,
    m.tournament_id,
    m.division,
    m.pod,
    m.round_number,
    m.table_number,
    m.status,
    m.player1_key,
    m.player2_key,
    d1.deck_url,
    d2.deck_url,
    m.player1_outcome,
    m.player2_outcome,
    m.player1_record,
    m.player2_record,
    m.player1_points,
    m.player2_points,
    p1.overall,
    p1.variant,
    p2.overall,
    p2.variant,
    m.player1_day_2_contention,
    m.player1_day_2,
    m.player2_day_2_contention,
    m.player2_day_2,
    CASE
        WHEN m.player1_outcome = 'win'
            AND m.player2_outcome = 'loss'
            THEN 'player1_win'
        WHEN m.player1_outcome = 'loss'
            AND m.player2_outcome = 'win'
            THEN 'player2_win'
        WHEN m.player1_outcome = 'loss'
            AND m.player2_outcome = 'loss'
            THEN 'unknown'
        ELSE 'tie_or_unknown'
    END AS match_result
"""


def get_matchup_connection() -> sqlite3.Connection:
    """Return a connection to the pairing database."""

    return sqlite3.connect(str(PAIRING_DATABASE_NAME))


def create_matchup_table() -> None:
    """Create the refreshable, player/deck-enriched matchup table."""

    conn = get_matchup_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matchup_records (
            match_key TEXT PRIMARY KEY,
            tournament_id TEXT NOT NULL,
            division TEXT NOT NULL,
            pod INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            table_number INTEGER,
            status TEXT NOT NULL,
            player1_key TEXT,
            player2_key TEXT,
            player1_deck_url TEXT,
            player2_deck_url TEXT,
            player1_outcome TEXT,
            player2_outcome TEXT,
            player1_record TEXT,
            player2_record TEXT,
            player1_points_after INTEGER,
            player2_points_after INTEGER,
            player1_points_before INTEGER,
            player2_points_before INTEGER,
            player1_overall TEXT,
            player1_variant TEXT,
            player2_overall TEXT,
            player2_variant TEXT,
            player1_day_2_contention INTEGER,
            player1_day_2 INTEGER,
            player2_day_2_contention INTEGER,
            player2_day_2 INTEGER,
            match_result TEXT NOT NULL,
            eligible_for_analytics INTEGER NOT NULL
        )
        """
    )
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(matchup_records)")
    }
    new_columns = {
        "player1_record": "TEXT",
        "player2_record": "TEXT",
        "player1_points_after": "INTEGER",
        "player2_points_after": "INTEGER",
        "player1_points_before": "INTEGER",
        "player2_points_before": "INTEGER",
        "player1_day_2_contention": "INTEGER",
        "player1_day_2": "INTEGER",
        "player2_day_2_contention": "INTEGER",
        "player2_day_2": "INTEGER",
    }
    for column, data_type in new_columns.items():
        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE matchup_records ADD COLUMN {column} {data_type}"
            )
    conn.commit()
    conn.close()


def _match_result(player1_outcome: str | None, player2_outcome: str | None) -> str:
    if player1_outcome == "win" and player2_outcome == "loss":
        return "player1_win"
    if player1_outcome == "loss" and player2_outcome == "win":
        return "player2_win"
    if player1_outcome == "loss" and player2_outcome == "loss":
        return "unknown"
    return "tie_or_unknown"


def _count_ties(results: pd.Series) -> int:
    """Count explicit tie results without crediting unknown outcomes."""

    return int((results == "tie_or_unknown").sum())


def _add_win_rates(
    summary: pd.DataFrame,
    wins_column: str = "wins",
    games_column: str = "games",
    ties_column: str = "ties_or_unknown",
) -> pd.DataFrame:
    """Add match-point and decisive-game win rates to an aggregate frame."""

    summary["decisive_games"] = summary[wins_column] + summary["losses"]
    summary["decisive_win_rate"] = summary[wins_column] / summary[
        "decisive_games"
    ].where(summary["decisive_games"] > 0)
    summary["win_rate"] = (
        summary[wins_column] + summary[ties_column] / 3
    ) / summary[games_column].where(summary[games_column] > 0)
    return summary


def _points_before(
    points_after: int | None,
    outcome: str | None,
    status: str,
) -> int | None:
    """Estimate pre-round points from RK9's post-round point total."""

    if points_after is None or status != "complete":
        return None
    if outcome == "win":
        return points_after - 3
    if outcome == "tie_or_unknown":
        return points_after - 1
    return points_after


def refresh_matchups(tournament_id: str | None = None) -> dict[str, int]:
    """Refresh enriched matchup records after classifications change.

    Pairing rows remain the raw RK9 source. This derived table joins each side
    to its deck URL and current archetype metadata, so changing classifications
    only requires this refresh rather than another RK9 scrape.
    """

    create_pairing_database()
    create_matchup_table()
    conn = get_matchup_connection()
    conn.execute("ATTACH DATABASE ? AS main_database", (str(DATABASE_NAME),))

    if tournament_id is None:
        source_rows = conn.execute(
            f"""
            SELECT {SOURCE_COLUMNS}
            FROM pairing_matches m
            LEFT JOIN main_database.players p1
                ON p1.player_key = m.player1_key
                AND p1.tournament_id = m.tournament_id
            LEFT JOIN main_database.players p2
                ON p2.player_key = m.player2_key
                AND p2.tournament_id = m.tournament_id
            LEFT JOIN main_database.decks d1
                ON d1.player_key = m.player1_key
            LEFT JOIN main_database.decks d2
                ON d2.player_key = m.player2_key
            """
        ).fetchall()
        conn.execute("DELETE FROM matchup_records")
    else:
        source_rows = conn.execute(
            f"""
            SELECT {SOURCE_COLUMNS}
            FROM pairing_matches m
            LEFT JOIN main_database.players p1
                ON p1.player_key = m.player1_key
                AND p1.tournament_id = m.tournament_id
            LEFT JOIN main_database.players p2
                ON p2.player_key = m.player2_key
                AND p2.tournament_id = m.tournament_id
            LEFT JOIN main_database.decks d1
                ON d1.player_key = m.player1_key
            LEFT JOIN main_database.decks d2
                ON d2.player_key = m.player2_key
            WHERE m.tournament_id = ?
            """,
            (tournament_id,),
        ).fetchall()
        conn.execute(
            "DELETE FROM matchup_records WHERE tournament_id = ?",
            (tournament_id,),
        )

    rows = []
    for row in source_rows:
        (
            match_key,
            event_id,
            division,
            pod,
            round_number,
            table_number,
            status,
            player1_key,
            player2_key,
            player1_deck_url,
            player2_deck_url,
            player1_outcome,
            player2_outcome,
            player1_record,
            player2_record,
            player1_points_after,
            player2_points_after,
            player1_overall,
            player1_variant,
            player2_overall,
            player2_variant,
            player1_day_2_contention,
            player1_day_2,
            player2_day_2_contention,
            player2_day_2,
            match_result,
        ) = row
        player1_points_before = _points_before(
            player1_points_after,
            player1_outcome,
            status,
        )
        player2_points_before = _points_before(
            player2_points_after,
            player2_outcome,
            status,
        )
        eligible = int(
            status == "complete"
            and player1_key is not None
            and player2_key is not None
            and player1_overall is not None
            and player2_overall is not None
        )
        rows.append(
            (
                match_key,
                event_id,
                division,
                pod,
                round_number,
                table_number,
                status,
                player1_key,
                player2_key,
                player1_deck_url,
                player2_deck_url,
                player1_outcome,
                player2_outcome,
                player1_record,
                player2_record,
                player1_points_after,
                player2_points_after,
                player1_points_before,
                player2_points_before,
                player1_overall,
                player1_variant,
                player2_overall,
                player2_variant,
                player1_day_2_contention,
                player1_day_2,
                player2_day_2_contention,
                player2_day_2,
                match_result,
                eligible,
            )
        )

    conn.executemany(
        f"INSERT OR REPLACE INTO matchup_records ({MATCHUP_COLUMNS}) "
        "VALUES (" + ", ".join(["?"] * 29) + ")",
        rows,
    )
    conn.commit()
    conn.close()

    return {
        "records": len(rows),
        "eligible": sum(row[-1] for row in rows),
    }


def get_matchup_records(
    tournament_id: str | None = None,
    division: str = "Masters",
    eligible_only: bool = True,
) -> pd.DataFrame:
    """Return enriched matchup records for analysis."""

    conn = get_matchup_connection()
    clauses = ["division = ?"]
    params: list[object] = [division]
    if tournament_id is not None:
        clauses.append("tournament_id = ?")
        params.append(tournament_id)
    if eligible_only:
        clauses.append("eligible_for_analytics = 1")

    query = (
        "SELECT * FROM matchup_records WHERE "
        + " AND ".join(clauses)
        + " ORDER BY tournament_id, round_number, table_number"
    )
    frame = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return frame


def summarize_archetype_matchups(
    tournament_id: str | None = None,
    division: str = "Masters",
    use_variants: bool = False,
    include_unknown: bool = False,
) -> pd.DataFrame:
    """Return canonical, unordered archetype matchup win/loss summaries.

    Ties and unknown outcomes remain visible in the output but are excluded
    from decisive-game win-rate denominators. Mirror matchups are retained,
    while their two directional win-rate fields are left null.
    """

    records = get_matchup_records(tournament_id, division)
    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    records = records.dropna(subset=[label1, label2]).copy()
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()

    if records.empty:
        return pd.DataFrame(
            columns=[
                "archetype_a",
                "archetype_b",
                "games",
                "a_wins",
                "b_wins",
                "ties_or_unknown",
                "decisive_games",
                "is_mirror",
                "a_win_rate",
                "b_win_rate",
                "a_decisive_win_rate",
                "b_decisive_win_rate",
            ]
        )

    records["archetype_a"] = records[[label1, label2]].min(axis=1)
    records["archetype_b"] = records[[label1, label2]].max(axis=1)
    records["a_wins"] = (
        ((records[label1] == records["archetype_a"]) & (records["match_result"] == "player1_win"))
        | ((records[label2] == records["archetype_a"]) & (records["match_result"] == "player2_win"))
    ).astype(int)
    records["b_wins"] = (
        ((records[label1] == records["archetype_b"]) & (records["match_result"] == "player1_win"))
        | ((records[label2] == records["archetype_b"]) & (records["match_result"] == "player2_win"))
    ).astype(int)
    records["tie_or_unknown"] = (
        records["match_result"] == "tie_or_unknown"
    ).astype(int)

    summary = (
        records.groupby(["archetype_a", "archetype_b"], as_index=False)
        .agg(
            games=("match_key", "count"),
            a_wins=("a_wins", "sum"),
            b_wins=("b_wins", "sum"),
            ties_or_unknown=("tie_or_unknown", "sum"),
        )
    )
    summary["decisive_games"] = summary["a_wins"] + summary["b_wins"]
    summary["is_mirror"] = summary["archetype_a"] == summary["archetype_b"]
    decisive = summary["decisive_games"].where(summary["decisive_games"] > 0)
    summary["a_decisive_win_rate"] = summary["a_wins"] / decisive
    summary["b_decisive_win_rate"] = summary["b_wins"] / decisive
    summary["a_win_rate"] = (
        summary["a_wins"] + summary["ties_or_unknown"] / 3
    ) / summary["games"].where(summary["games"] > 0)
    summary["b_win_rate"] = (
        summary["b_wins"] + summary["ties_or_unknown"] / 3
    ) / summary["games"].where(summary["games"] > 0)
    summary.loc[
        summary["is_mirror"],
        [
            "a_win_rate",
            "b_win_rate",
            "a_decisive_win_rate",
            "b_decisive_win_rate",
        ],
    ] = pd.NA
    return summary.sort_values(["games", "archetype_a", "archetype_b"], ascending=[False, True, True])


def get_archetype_matchup_matrix(
    tournament_id: str | None = None,
    division: str = "Masters",
    use_variants: bool = False,
    include_unknown: bool = False,
) -> pd.DataFrame:
    """Return a directed archetype win-rate matrix.

    Rows are the focal archetype and columns are opposing archetypes. Values
    are match-point-adjusted win rates, where a tie contributes one third of
    a win. Mirror cells represent the archetype's combined win rate across
    both sides of the mirror.
    """

    records = get_matchup_records(tournament_id, division)
    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    records = records.dropna(subset=[label1, label2]).copy()
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()

    if records.empty:
        return pd.DataFrame()

    directed = pd.concat(
        [
            records[[label1, label2, "match_result"]].rename(
                columns={label1: "archetype", label2: "opponent"}
            ).assign(
                wins=lambda frame: (frame["match_result"] == "player1_win").astype(int),
                losses=lambda frame: (frame["match_result"] == "player2_win").astype(int),
                ties=lambda frame: (frame["match_result"] == "tie_or_unknown").astype(int),
            ),
            records[[label2, label1, "match_result"]].rename(
                columns={label2: "archetype", label1: "opponent"}
            ).assign(
                wins=lambda frame: (frame["match_result"] == "player2_win").astype(int),
                losses=lambda frame: (frame["match_result"] == "player1_win").astype(int),
                ties=lambda frame: (frame["match_result"] == "tie_or_unknown").astype(int),
            ),
        ],
        ignore_index=True,
    )
    summary = (
        directed.groupby(["archetype", "opponent"], as_index=False)
        .agg(
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("ties", "sum"),
        )
    )
    _add_win_rates(summary)
    return summary.pivot(
        index="archetype",
        columns="opponent",
        values="win_rate",
    ).sort_index().sort_index(axis=1)


def get_archetype_matchup_trends(
    archetype: str | None = None,
    opponent: str | None = None,
    division: str = "Masters",
    use_variants: bool = False,
    include_unknown: bool = False,
) -> pd.DataFrame:
    """Return directed matchup performance separately for each tournament."""

    records = get_matchup_records(division=division)
    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    records = records.dropna(subset=[label1, label2]).copy()
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()

    directed = pd.concat(
        [
            records[["tournament_id", label1, label2, "match_result"]].rename(
                columns={label1: "archetype", label2: "opponent"}
            ).assign(
                wins=lambda frame: (frame["match_result"] == "player1_win").astype(int),
                losses=lambda frame: (frame["match_result"] == "player2_win").astype(int),
            ),
            records[["tournament_id", label2, label1, "match_result"]].rename(
                columns={label2: "archetype", label1: "opponent"}
            ).assign(
                wins=lambda frame: (frame["match_result"] == "player2_win").astype(int),
                losses=lambda frame: (frame["match_result"] == "player1_win").astype(int),
            ),
        ],
        ignore_index=True,
    )
    if archetype is not None:
        directed = directed[directed["archetype"] == archetype]
    if opponent is not None:
        directed = directed[directed["opponent"] == opponent]

    summary = (
        directed.groupby(
            ["tournament_id", "archetype", "opponent"],
            as_index=False,
        )
        .agg(
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("match_result", _count_ties),
        )
    )
    _add_win_rates(summary)
    return summary.sort_values(
        ["tournament_id", "games", "archetype", "opponent"],
        ascending=[True, False, True, True],
    ).reset_index(drop=True)


def get_multi_tournament_matchup_summary(
    tournament_ids: list[str] | None = None,
    archetype: str | None = None,
    opponent: str | None = None,
    division: str = "Masters",
    use_variants: bool = False,
    include_unknown: bool = False,
) -> pd.DataFrame:
    """Return aggregated directed matchup results across tournaments.

    Each completed pairing contributes one directed result for each player.
    When ``tournament_ids`` is omitted, all tournaments in the pairing
    database are included. Ties remain in ``games`` and contribute one third
    of a win to ``win_rate``; ``decisive_win_rate`` excludes them.
    """

    records = get_matchup_records(division=division)
    if tournament_ids is not None:
        records = records[records["tournament_id"].isin(tournament_ids)].copy()
    if records.empty:
        return pd.DataFrame()

    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    records = records.dropna(subset=[label1, label2]).copy()
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()
    if records.empty:
        return pd.DataFrame()

    directed = pd.concat(
        [
            records[
                [
                    "tournament_id",
                    label1,
                    label2,
                    "player1_key",
                    "match_result",
                ]
            ].rename(
                columns={
                    label1: "archetype",
                    label2: "opponent",
                    "player1_key": "player_key",
                }
            ).assign(
                wins=lambda frame: (
                    frame["match_result"] == "player1_win"
                ).astype(int),
                losses=lambda frame: (
                    frame["match_result"] == "player2_win"
                ).astype(int),
            ),
            records[
                [
                    "tournament_id",
                    label2,
                    label1,
                    "player2_key",
                    "match_result",
                ]
            ].rename(
                columns={
                    label2: "archetype",
                    label1: "opponent",
                    "player2_key": "player_key",
                }
            ).assign(
                wins=lambda frame: (
                    frame["match_result"] == "player2_win"
                ).astype(int),
                losses=lambda frame: (
                    frame["match_result"] == "player1_win"
                ).astype(int),
            ),
        ],
        ignore_index=True,
    )
    if archetype is not None:
        directed = directed[directed["archetype"] == archetype]
    if opponent is not None:
        directed = directed[directed["opponent"] == opponent]
    if directed.empty:
        return pd.DataFrame()

    summary = (
        directed.groupby(["archetype", "opponent"], as_index=False)
        .agg(
            tournaments=("tournament_id", "nunique"),
            players=("player_key", "nunique"),
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("match_result", _count_ties),
        )
    )
    _add_win_rates(summary)
    return summary.sort_values(
        ["games", "archetype", "opponent"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def get_matchup_strength_cohorts(
    round_number: int,
    tournament_id: str | None = None,
    division: str = "Masters",
    snapshot: str = "before",
    use_variants: bool = False,
    include_unknown: bool = False,
    min_games: int = 1,
) -> pd.DataFrame:
    """Compare matchup results by the opponent's points at a round.

    ``snapshot='before'`` is the default because it measures opponent
    strength before the selected round's result is known. ``after`` uses the
    points displayed by RK9 after that round.
    """

    if snapshot not in {"before", "after"}:
        raise ValueError("snapshot must be 'before' or 'after'")

    records = get_matchup_records(tournament_id, division)
    records = records[records["round_number"] == round_number].copy()
    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    points1 = f"player1_points_{snapshot}"
    points2 = f"player2_points_{snapshot}"
    records = records.dropna(subset=[label1, label2, points1, points2])
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()

    directed = pd.concat(
        [
            records[[label1, label2, points2, "match_result"]].rename(
                columns={
                    label1: "archetype",
                    label2: "opponent",
                    points2: "opponent_points",
                }
            ).assign(
                wins=lambda frame: (frame["match_result"] == "player1_win").astype(int),
                losses=lambda frame: (frame["match_result"] == "player2_win").astype(int),
            ),
            records[[label2, label1, points1, "match_result"]].rename(
                columns={
                    label2: "archetype",
                    label1: "opponent",
                    points1: "opponent_points",
                }
            ).assign(
                wins=lambda frame: (frame["match_result"] == "player2_win").astype(int),
                losses=lambda frame: (frame["match_result"] == "player1_win").astype(int),
            ),
        ],
        ignore_index=True,
    )
    summary = (
        directed.groupby(
            ["opponent_points", "archetype", "opponent"],
            as_index=False,
        )
        .agg(
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("match_result", _count_ties),
        )
    )
    _add_win_rates(summary)
    summary["matchup"] = (
        summary["archetype"] + " vs " + summary["opponent"]
    )
    return summary[summary["games"] >= min_games].sort_values(
        ["opponent_points", "games", "matchup"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def get_matchup_strength_matrix(
    round_number: int,
    tournament_id: str | None = None,
    division: str = "Masters",
    snapshot: str = "before",
    use_variants: bool = False,
    include_unknown: bool = False,
    min_games: int = 1,
) -> pd.DataFrame:
    """Return strength-cohort win rates as points rows and matchups columns."""

    cohorts = get_matchup_strength_cohorts(
        round_number=round_number,
        tournament_id=tournament_id,
        division=division,
        snapshot=snapshot,
        use_variants=use_variants,
        include_unknown=include_unknown,
        min_games=min_games,
    )
    if cohorts.empty:
        return pd.DataFrame()
    return cohorts.pivot(
        index="opponent_points",
        columns="matchup",
        values="win_rate",
    ).sort_index().sort_index(axis=1)


DAY_TWO_RULES = (
    (65, 128, 7, 13),
    (129, 256, 8, 16),
    (257, 512, 8, 16),
    (513, 1024, 8, 16),
    (1025, 2048, 8, 16),
    (2049, 4096, 8, 16),
    (4097, 8192, 9, 19),
)


def _day_two_rule(player_count: int) -> tuple[int, int] | None:
    """Return phase-one rounds and the Day 2 point threshold."""

    for minimum, maximum, phase_one_rounds, threshold in DAY_TWO_RULES:
        if minimum <= player_count <= maximum:
            return phase_one_rounds, threshold
    return None


def _division_player_counts() -> dict[tuple[str, str], int]:
    """Load tournament/division field sizes from the primary database."""

    conn = sqlite3.connect(str(DATABASE_NAME))
    rows = conn.execute(
        """
        SELECT tournament_id, division, COUNT(*)
        FROM players
        GROUP BY tournament_id, division
        """
    ).fetchall()
    conn.close()
    return {(row[0], row[1]): row[2] for row in rows}


def _is_day_two_contender(
    points_before: float | None,
    round_number: int,
    rule: tuple[int, int] | None,
) -> bool | None:
    """Determine whether a player can still reach the Day 2 threshold."""

    if rule is None or points_before is None:
        return None
    phase_one_rounds, threshold = rule
    remaining_rounds = max(phase_one_rounds - round_number + 1, 0)
    return points_before + (remaining_rounds * 3) >= threshold


def refresh_day_two_fields(tournament_id: str | None = None) -> dict[str, int]:
    """Persist per-round contention and final Day 2 flags upstream.

    ``*_day_2_contention`` describes whether the player could still reach the
    Day 2 threshold before that pairing. ``*_day_2`` is the final 1/0 result
    after the phase-one rounds. Both values are written to raw pairing rows,
    enriched matchup rows, and the primary ``players`` table.
    """

    create_pairing_database()
    create_matchup_table()
    conn = get_matchup_connection()
    conn.execute("ATTACH DATABASE ? AS main_database", (str(DATABASE_NAME),))
    clauses = []
    params: list[object] = []
    if tournament_id is not None:
        clauses.append("m.tournament_id = ?")
        params.append(tournament_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"""
        SELECT
            m.match_key, m.tournament_id, m.division, m.round_number,
            m.status, m.player1_key, m.player1_points, m.player1_outcome,
            m.player2_key, m.player2_points, m.player2_outcome
        FROM pairing_matches m
        {where}
        """,
        params,
    ).fetchall()

    field_sizes = _division_player_counts()
    player_flags: dict[tuple[str, str], dict[str, int]] = {}
    match_updates = []
    for row in rows:
        (
            match_key,
            event_id,
            division,
            round_number,
            status,
            player1_key,
            player1_points,
            player1_outcome,
            player2_key,
            player2_points,
            player2_outcome,
        ) = row
        rule = _day_two_rule(field_sizes.get((event_id, division), 0))
        p1_before = _points_before(player1_points, player1_outcome, status)
        p2_before = _points_before(player2_points, player2_outcome, status)
        p1_contention = _is_day_two_contender(p1_before, int(round_number), rule)
        p2_contention = _is_day_two_contender(p2_before, int(round_number), rule)
        p1_day_2 = None
        p2_day_2 = None
        if rule is not None and status == "complete":
            phase_one_rounds, threshold = rule
            if int(round_number) == phase_one_rounds:
                p1_day_2 = int(
                    player1_points is not None and player1_points >= threshold
                )
                p2_day_2 = int(
                    player2_points is not None and player2_points >= threshold
                )
                if player1_key is not None:
                    player_flags[(event_id, division)] = player_flags.get(
                        (event_id, division), {}
                    )
                    player_flags[(event_id, division)][player1_key] = p1_day_2
                if player2_key is not None:
                    player_flags[(event_id, division)] = player_flags.get(
                        (event_id, division), {}
                    )
                    player_flags[(event_id, division)][player2_key] = p2_day_2
        match_updates.append(
            (int(p1_contention) if p1_contention is not None else None,
             p1_day_2,
             int(p2_contention) if p2_contention is not None else None,
             p2_day_2,
             match_key)
        )

    conn.executemany(
        """
        UPDATE pairing_matches
        SET player1_day_2_contention = ?, player1_day_2 = ?,
            player2_day_2_contention = ?, player2_day_2 = ?
        WHERE match_key = ?
        """,
        match_updates,
    )
    conn.executemany(
        """
        UPDATE matchup_records
        SET player1_day_2_contention = ?, player1_day_2 = ?,
            player2_day_2_contention = ?, player2_day_2 = ?
        WHERE match_key = ?
        """,
        match_updates,
    )

    # The final Day 2 result is a player-level field. Persist it on every
    # pairing row using a temporary lookup table so the migration stays
    # set-based even when a tournament has thousands of players.
    flag_rows = [
        (event_id, division, player_key, day_2)
        for (event_id, division), flags in player_flags.items()
        for player_key, day_2 in flags.items()
    ]
    conn.execute(
        """
        CREATE TEMP TABLE day_two_flags (
            tournament_id TEXT,
            division TEXT,
            player_key TEXT,
            day_2 INTEGER,
            PRIMARY KEY (tournament_id, division, player_key)
        )
        """
    )
    conn.executemany(
        "INSERT INTO day_two_flags VALUES (?, ?, ?, ?)",
        flag_rows,
    )
    for event_id, division in field_sizes:
        if tournament_id is not None and event_id != tournament_id:
            continue
        flags = player_flags.get((event_id, division), {})
        players = conn.execute(
            """
            SELECT player_key
            FROM main_database.players
            WHERE tournament_id = ? AND division = ?
            """,
            (event_id, division),
        ).fetchall()
        conn.executemany(
            """
            INSERT OR IGNORE INTO day_two_flags
                (tournament_id, division, player_key, day_2)
            VALUES (?, ?, ?, ?)
            """,
            [
                (event_id, division, row[0], flags.get(row[0], 0))
                for row in players
            ],
        )
    conn.execute(
        """
        UPDATE pairing_matches
        SET player1_day_2 = (
            SELECT day_2 FROM day_two_flags f
            WHERE f.tournament_id = pairing_matches.tournament_id
              AND f.division = pairing_matches.division
              AND f.player_key = pairing_matches.player1_key
        )
        WHERE player1_key IS NOT NULL
        """
    )
    conn.execute(
        """
        UPDATE pairing_matches
        SET player2_day_2 = (
            SELECT day_2 FROM day_two_flags f
            WHERE f.tournament_id = pairing_matches.tournament_id
              AND f.division = pairing_matches.division
              AND f.player_key = pairing_matches.player2_key
        )
        WHERE player2_key IS NOT NULL
        """
    )
    conn.execute(
        """
        UPDATE matchup_records
        SET player1_day_2 = (
            SELECT day_2 FROM day_two_flags f
            WHERE f.tournament_id = matchup_records.tournament_id
              AND f.division = matchup_records.division
              AND f.player_key = matchup_records.player1_key
        )
        WHERE player1_key IS NOT NULL
        """
    )
    conn.execute(
        """
        UPDATE matchup_records
        SET player2_day_2 = (
            SELECT day_2 FROM day_two_flags f
            WHERE f.tournament_id = matchup_records.tournament_id
              AND f.division = matchup_records.division
              AND f.player_key = matchup_records.player2_key
        )
        WHERE player2_key IS NOT NULL
        """
    )

    player_updates = []
    for event_id, division in field_sizes:
        if tournament_id is not None and event_id != tournament_id:
            continue
        flags = player_flags.get((event_id, division), {})
        players = conn.execute(
            """
            SELECT player_key
            FROM main_database.players
            WHERE tournament_id = ? AND division = ?
            """,
            (event_id, division),
        ).fetchall()
        player_updates.extend(
            (flags.get(row[0], 0), row[0], event_id)
            for row in players
        )
    conn.executemany(
        "UPDATE main_database.players SET day_2 = ? WHERE player_key = ? AND tournament_id = ?",
        player_updates,
    )
    conn.commit()
    conn.close()
    return {
        "pairings": len(rows),
        "player_flags": len(player_updates),
    }


def get_matchup_round_cohorts(
    tournament_id: str | None = None,
    division: str = "Masters",
    cumulative: bool = False,
    max_round: int | None = None,
    day_2_contention: bool | None = None,
    use_variants: bool = False,
    include_unknown: bool = False,
    min_games: int = 1,
) -> pd.DataFrame:
    """Return matchup rates by round and optional Day 2 contention status.

    With ``cumulative=True``, the row for round N includes matches from rounds
    1 through N. Contention is evaluated before each match using the TCG
    phase-one rules and the opponent's available match points.
    """

    records = get_matchup_records(tournament_id, division)
    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    records = records.dropna(
        subset=[
            label1,
            label2,
            "player1_day_2_contention",
            "player2_day_2_contention",
        ]
    ).copy()
    if max_round is not None:
        records = records[records["round_number"] <= max_round]
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()

    directed_frames = []
    for _, record in records.iterrows():
        round_number = int(record["round_number"])
        p1_contention = bool(record["player1_day_2_contention"])
        p2_contention = bool(record["player2_day_2_contention"])
        directed_frames.extend(
            [
                {
                    "match_round": round_number,
                    "archetype": record[label1],
                    "opponent": record[label2],
                    "day_2_contention": p2_contention,
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player1_win"),
                    "losses": int(record["match_result"] == "player2_win"),
                },
                {
                    "match_round": round_number,
                    "archetype": record[label2],
                    "opponent": record[label1],
                    "day_2_contention": p1_contention,
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player2_win"),
                    "losses": int(record["match_result"] == "player1_win"),
                },
            ]
        )

    directed = pd.DataFrame(directed_frames)
    if directed.empty:
        return pd.DataFrame()
    if day_2_contention is not None:
        directed = directed[
            directed["day_2_contention"] == day_2_contention
        ].copy()
    if directed.empty:
        return pd.DataFrame()

    final_round = max_round or int(directed["match_round"].max())
    if cumulative:
        directed["round"] = directed["match_round"].apply(
            lambda round_number: list(range(round_number, final_round + 1))
        )
        directed = directed.explode("round")
    else:
        directed["round"] = directed["match_round"]

    summary = (
        directed.groupby(
            ["round", "archetype", "opponent", "day_2_contention"],
            as_index=False,
        )
        .agg(
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("match_result", _count_ties),
        )
    )
    _add_win_rates(summary)
    summary["matchup"] = (
        summary["archetype"] + " vs " + summary["opponent"]
    )
    summary["day_2_contention"] = summary["day_2_contention"].map(
        {True: "yes", False: "no"}
    ).fillna("not_applicable")
    if day_2_contention is None:
        all_summary = (
            directed.groupby(["round", "archetype", "opponent"], as_index=False)
            .agg(
                games=("match_result", "count"),
                wins=("wins", "sum"),
                losses=("losses", "sum"),
                ties_or_unknown=("match_result", _count_ties),
            )
        )
        _add_win_rates(all_summary)
        all_summary["day_2_contention"] = "all"
        all_summary["matchup"] = (
            all_summary["archetype"] + " vs " + all_summary["opponent"]
        )
        summary = pd.concat([summary, all_summary], ignore_index=True)

    status_order = {"all": 0, "yes": 1, "no": 2, "not_applicable": 3}
    summary["_status_order"] = summary["day_2_contention"].map(status_order)
    return summary[summary["games"] >= min_games].sort_values(
        ["round", "matchup", "_status_order"],
        ascending=[True, True, True],
    ).drop(columns="_status_order").reset_index(drop=True)


def get_matchup_round_matrix(
    **kwargs: object,
) -> pd.DataFrame:
    """Return round matchup win rates with rounds as the index."""

    cohorts = get_matchup_round_cohorts(**kwargs)
    if cohorts.empty:
        return pd.DataFrame()
    grouped = (
        cohorts.groupby(["round", "matchup"], as_index=False)
        .agg(
            games=("games", "sum"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("ties_or_unknown", "sum"),
        )
    )
    _add_win_rates(grouped)
    return grouped.pivot(
        index="round",
        columns="matchup",
        values="win_rate",
    ).sort_index().sort_index(axis=1)


def flatten_matchup_round_cohorts(cohorts: pd.DataFrame) -> pd.DataFrame:
    """Collapse round-level matchup rows into tournament totals."""

    if cohorts.empty:
        return cohorts.copy()

    totals = (
        cohorts.groupby(
            ["archetype", "opponent", "day_2_contention"],
            as_index=False,
        )
        .agg(
            games=("games", "sum"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("ties_or_unknown", "sum"),
        )
    )
    _add_win_rates(totals)
    totals["round"] = "TOTAL"
    totals["matchup"] = totals["archetype"] + " vs " + totals["opponent"]
    return totals[
        [
            "round",
            "matchup",
            "day_2_contention",
            "games",
            "wins",
            "losses",
            "ties_or_unknown",
            "win_rate",
        ]
    ].sort_values(["matchup", "day_2_contention"]).reset_index(drop=True)


def get_archetype_field_performance(
    tournament_id: str | None = None,
    division: str = "Masters",
    use_variants: bool = False,
    include_unknown: bool = False,
    max_round: int | None = None,
) -> pd.DataFrame:
    """Return each archetype's performance against the entire field.

    Each completed pairing contributes one directed result for each player, so
    the result describes the selected archetype from its own perspective. Ties
    remain in ``games`` but are excluded from ``win_rate``'s denominator.
    """

    records = get_matchup_records(tournament_id, division)
    if records.empty:
        return pd.DataFrame()
    if max_round is not None:
        records = records[records["round_number"] <= max_round].copy()

    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()
    records = records.dropna(subset=[label1, label2])
    if records.empty:
        return pd.DataFrame()

    directed_frames = []
    for _, record in records.iterrows():
        directed_frames.extend(
            [
                {
                    "tournament_id": record["tournament_id"],
                    "archetype": record[label1],
                    "player_key": record["player1_key"],
                    "opponent": record[label2],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player1_win"),
                    "losses": int(record["match_result"] == "player2_win"),
                },
                {
                    "tournament_id": record["tournament_id"],
                    "archetype": record[label2],
                    "player_key": record["player2_key"],
                    "opponent": record[label1],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player2_win"),
                    "losses": int(record["match_result"] == "player1_win"),
                },
            ]
        )

    directed = pd.DataFrame(directed_frames)
    if directed.empty:
        return pd.DataFrame()

    group_columns = ["archetype"]
    if tournament_id is None:
        group_columns.insert(0, "tournament_id")
    summary = (
        directed.groupby(group_columns, as_index=False)
        .agg(
            players=("player_key", "nunique"),
            opponents=("opponent", "nunique"),
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("match_result", _count_ties),
        )
    )
    _add_win_rates(summary)
    return summary.sort_values(
        ["win_rate", "games", "archetype"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)


def get_card_matchup_performance(
    tournament_id: str,
    archetype: str,
    opponent: str,
    division: str = "Masters",
    use_variants: bool = False,
) -> pd.DataFrame:
    """Compare card-level results inside one directed archetype matchup.

    Each selected-archetype player contributes one directed result per game.
    For every card found in those deck lists, the report compares games where
    the card was present with games where it was absent. Win rates use the
    project's match-point convention, so ties contribute one third of a win.
    """

    records = get_matchup_records(tournament_id, division)
    if records.empty:
        return pd.DataFrame()

    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    directed_rows = []
    for _, record in records.iterrows():
        if record[label1] == archetype and record[label2] == opponent:
            directed_rows.append(
                {
                    "player_key": record["player1_key"],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player1_win"),
                    "losses": int(record["match_result"] == "player2_win"),
                }
            )
        if record[label2] == archetype and record[label1] == opponent:
            directed_rows.append(
                {
                    "player_key": record["player2_key"],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player2_win"),
                    "losses": int(record["match_result"] == "player1_win"),
                }
            )

    directed = pd.DataFrame(directed_rows)
    if directed.empty:
        return pd.DataFrame()
    directed = directed[directed["match_result"] != "unknown"].copy()
    if directed.empty:
        return pd.DataFrame()
    directed["ties"] = (
        directed["match_result"] == "tie_or_unknown"
    ).astype(int)

    conn = sqlite3.connect(str(DATABASE_NAME))
    player_keys = directed["player_key"].dropna().unique().tolist()
    placeholders = ", ".join("?" for _ in player_keys)
    cards = pd.read_sql_query(
        f"""
        SELECT player_key, card_name, quantity
        FROM deck_cards
        WHERE player_key IN ({placeholders})
        """,
        conn,
        params=player_keys,
    )
    conn.close()
    if cards.empty:
        return pd.DataFrame()

    card_sets = (
        cards.groupby("player_key")["card_name"]
        .apply(set)
        .to_dict()
    )
    card_names = sorted(cards["card_name"].dropna().unique())
    rows = []
    for card_name in card_names:
        present = directed["player_key"].map(
            lambda player_key: card_name in card_sets.get(player_key, set())
        )
        card_rows = []
        for is_present, label in ((True, "with_card"), (False, "without_card")):
            subset = directed[present == is_present]
            games = len(subset)
            wins = int(subset["wins"].sum())
            losses = int(subset["losses"].sum())
            ties = int(subset["ties"].sum())
            win_rate = (
                (wins + ties / 3) / games
                if games
                else None
            )
            card_rows.append((label, games, wins, losses, ties, win_rate))

        with_card, without_card = card_rows
        rows.append(
            {
                "card_name": card_name,
                "players_with_card": int(
                    sum(card_name in card_sets.get(key, set()) for key in player_keys)
                ),
                "games_with_card": with_card[1],
                "wins_with_card": with_card[2],
                "losses_with_card": with_card[3],
                "ties_with_card": with_card[4],
                "win_rate_with_card": with_card[5],
                "games_without_card": without_card[1],
                "wins_without_card": without_card[2],
                "losses_without_card": without_card[3],
                "ties_without_card": without_card[4],
                "win_rate_without_card": without_card[5],
            }
        )

    report = pd.DataFrame(rows)
    report["win_rate_delta"] = (
        report["win_rate_with_card"] - report["win_rate_without_card"]
    )
    report["archetype"] = archetype
    report["opponent"] = opponent
    report["grouping"] = "variant" if use_variants else "archetype"
    return report.sort_values(
        ["win_rate_delta", "games_with_card", "card_name"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)


def get_tech_card_matchup_analysis(
    tournament_id: str | None,
    archetype: str,
    card_name: str,
    division: str = "Masters",
    use_variants: bool = False,
    variant: str | None = None,
) -> pd.DataFrame:
    """Return matchup results against opponents with or without a card.

    The selected ``archetype`` is the focal deck whose performance is measured.
    ``card_name`` is checked in the opponent's deck, so the report compares
    focal-archetype results against opponents with and without that card.
    When ``variant`` is supplied, the focal deck must match both the overall
    archetype and that variant. Otherwise, when ``use_variants`` is true,
    ``archetype`` matches an overall archetype when possible, allowing all of
    its variants to be analyzed together. If it matches only a variant label,
    that variant is selected. Both sides include match-point win rate, tie
    rate, and decisive win rate.
    """

    records = get_matchup_records(tournament_id, division)
    if records.empty:
        return pd.DataFrame()

    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    overall_labels = {
        value
        for value in pd.concat(
            [records["player1_overall"], records["player2_overall"]]
        ).dropna()
    }

    def is_selected(record: pd.Series, side: int) -> bool:
        overall = record[f"player{side}_overall"]
        selected_variant = record[f"player{side}_variant"]
        selected_label = record[
            f"player{side}_{'variant' if use_variants else 'overall'}"
        ]
        if variant is not None:
            return overall == archetype and selected_variant == variant
        if use_variants and archetype in overall_labels:
            return overall == archetype
        return selected_label == archetype

    directed_rows = []
    for _, record in records.iterrows():
        if is_selected(record, 1):
            directed_rows.append(
                {
                    "player_key": record["player1_key"],
                    "opponent_player_key": record["player2_key"],
                    "opponent": record[label2],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player1_win"),
                    "losses": int(record["match_result"] == "player2_win"),
                }
            )
        if is_selected(record, 2):
            directed_rows.append(
                {
                    "player_key": record["player2_key"],
                    "opponent_player_key": record["player1_key"],
                    "opponent": record[label1],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player2_win"),
                    "losses": int(record["match_result"] == "player1_win"),
                }
            )

    directed = pd.DataFrame(directed_rows)
    if directed.empty:
        return pd.DataFrame()
    directed = directed[
        (directed["match_result"] != "unknown")
        & directed["opponent"].notna()
        & (directed["opponent"] != "Unknown")
    ].copy()
    if directed.empty:
        return pd.DataFrame()

    conn = sqlite3.connect(str(DATABASE_NAME))
    player_keys = (
        directed["opponent_player_key"]
        .dropna()
        .unique()
        .tolist()
    )
    if not player_keys:
        conn.close()
        return pd.DataFrame()
    placeholders = ", ".join("?" for _ in player_keys)
    cards = pd.read_sql_query(
        f"""
        SELECT player_key, card_name
        FROM deck_cards
        WHERE player_key IN ({placeholders})
        """,
        conn,
        params=player_keys,
    )
    conn.close()
    if cards.empty:
        return pd.DataFrame()

    card_players = set(
        cards.loc[cards["card_name"] == card_name, "player_key"]
    )
    directed["card_present"] = directed["opponent_player_key"].isin(
        card_players
    )
    directed["ties"] = (
        directed["match_result"] == "tie_or_unknown"
    ).astype(int)

    grouped = (
        directed.groupby(["opponent", "card_present"], as_index=False)
        .agg(
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties=("ties", "sum"),
            players=("player_key", "nunique"),
        )
    )
    grouped["win_rate"] = (
        grouped["wins"] + grouped["ties"] / 3
    ) / grouped["games"]
    grouped["tie_rate"] = grouped["ties"] / grouped["games"]
    grouped["decisive_games"] = grouped["wins"] + grouped["losses"]
    grouped["decisive_win_rate"] = grouped["wins"] / grouped[
        "decisive_games"
    ].where(grouped["decisive_games"] > 0)

    report = grouped.pivot(
        index="opponent",
        columns="card_present",
        values=[
            "players",
            "games",
            "wins",
            "losses",
            "ties",
            "win_rate",
            "tie_rate",
            "decisive_games",
            "decisive_win_rate",
        ],
    )
    report = report.reindex(
        columns=pd.MultiIndex.from_product(
            [
                [
                    "players",
                    "games",
                    "wins",
                    "losses",
                    "ties",
                    "win_rate",
                    "tie_rate",
                    "decisive_games",
                    "decisive_win_rate",
                ],
                [False, True],
            ],
            names=["metric", "card_present"],
        ),
        fill_value=0,
    )
    report.columns = [
        f"{metric}_{'with_card' if present else 'without_card'}"
        for metric, present in report.columns
    ]
    report = report.reset_index()
    for presence in ("with_card", "without_card"):
        no_games = report[f"games_{presence}"] == 0
        report.loc[
            no_games,
            [
                f"win_rate_{presence}",
                f"tie_rate_{presence}",
                f"decisive_win_rate_{presence}",
            ],
        ] = float("nan")
    report["win_rate_delta"] = (
        report["win_rate_with_card"] - report["win_rate_without_card"]
    )
    report["tie_rate_delta"] = (
        report["tie_rate_with_card"] - report["tie_rate_without_card"]
    )
    report["card_name"] = card_name
    report["archetype"] = archetype
    report["grouping"] = "variant" if use_variants else "archetype"
    return report.sort_values(
        ["games_with_card", "win_rate_delta", "opponent"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def get_tech_card_value_analysis(
    tournament_id: str | None,
    archetype: str,
    card_name: str,
    division: str = "Masters",
    use_variants: bool = False,
    variant: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Estimate the value of a card in the selected archetype's deck.

    The selected archetype is the focal deck. Results compare focal-deck games
    where the focal deck contains ``card_name`` with games where it does not.
    The returned reports include matchup value, round exposure, and a summary
    with a field-weighted replacement score. The score is measured in
    match-point percentage points per game, not a causal estimate.
    """

    records = get_matchup_records(tournament_id, division)
    if records.empty:
        return {
            "summary": pd.DataFrame(),
            "matchups": pd.DataFrame(),
            "rounds": pd.DataFrame(),
            "exposure": pd.DataFrame(),
            "meta_share": pd.DataFrame(),
        }

    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    overall_labels = {
        value
        for value in pd.concat(
            [records["player1_overall"], records["player2_overall"]]
        ).dropna()
    }

    def is_selected(record: pd.Series, side: int) -> bool:
        overall = record[f"player{side}_overall"]
        selected_variant = record[f"player{side}_variant"]
        selected_label = record[
            f"player{side}_{'variant' if use_variants else 'overall'}"
        ]
        if variant is not None:
            return overall == archetype and selected_variant == variant
        if use_variants and archetype in overall_labels:
            return overall == archetype
        return selected_label == archetype

    directed_rows = []
    for _, record in records.iterrows():
        if is_selected(record, 1):
            directed_rows.append(
                {
                    "tournament_id": record["tournament_id"],
                    "round": int(record["round_number"]),
                    "player_key": record["player1_key"],
                    "opponent": record[label2],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player1_win"),
                    "losses": int(record["match_result"] == "player2_win"),
                }
            )
        if is_selected(record, 2):
            directed_rows.append(
                {
                    "tournament_id": record["tournament_id"],
                    "round": int(record["round_number"]),
                    "player_key": record["player2_key"],
                    "opponent": record[label1],
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player2_win"),
                    "losses": int(record["match_result"] == "player1_win"),
                }
            )

    directed = pd.DataFrame(directed_rows)
    if directed.empty:
        return {
            "summary": pd.DataFrame(),
            "matchups": pd.DataFrame(),
            "rounds": pd.DataFrame(),
            "exposure": pd.DataFrame(),
            "meta_share": pd.DataFrame(),
        }
    directed = directed[
        (directed["match_result"] != "unknown")
        & directed["opponent"].notna()
        & (directed["opponent"] != "Unknown")
    ].copy()
    if directed.empty:
        return {
            "summary": pd.DataFrame(),
            "matchups": pd.DataFrame(),
            "rounds": pd.DataFrame(),
            "exposure": pd.DataFrame(),
            "meta_share": pd.DataFrame(),
        }

    conn = sqlite3.connect(str(DATABASE_NAME))
    player_keys = directed["player_key"].dropna().unique().tolist()
    placeholders = ", ".join("?" for _ in player_keys)
    cards = pd.read_sql_query(
        f"SELECT player_key, card_name FROM deck_cards WHERE player_key IN ({placeholders})",
        conn,
        params=player_keys,
    )
    conn.close()
    card_players = set(cards.loc[cards["card_name"] == card_name, "player_key"])
    directed["card_present"] = directed["player_key"].isin(card_players)
    directed["ties"] = (directed["match_result"] == "tie_or_unknown").astype(int)

    def add_rates(frame: pd.DataFrame) -> pd.DataFrame:
        frame = frame.copy()
        frame["win_rate"] = (
            frame["wins"] + frame["ties"] / 3
        ) / frame["games"]
        frame["tie_rate"] = frame["ties"] / frame["games"]
        frame["decisive_games"] = frame["wins"] + frame["losses"]
        frame["decisive_win_rate"] = frame["wins"] / frame["decisive_games"].where(
            frame["decisive_games"] > 0
        )
        return frame

    grouped = (
        directed.groupby(["opponent", "card_present"], as_index=False)
        .agg(
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties=("ties", "sum"),
            players=("player_key", "nunique"),
        )
    )
    grouped = add_rates(grouped)
    opponent_totals = directed.groupby("opponent").size().rename("opponent_games")
    grouped = grouped.merge(opponent_totals, on="opponent")
    grouped["opponent_field_share"] = grouped["opponent_games"] / len(directed)

    report = grouped.pivot(
        index="opponent",
        columns="card_present",
        values=[
            "players",
            "games",
            "wins",
            "losses",
            "ties",
            "win_rate",
            "tie_rate",
            "decisive_games",
            "decisive_win_rate",
        ],
    ).reindex(
        columns=pd.MultiIndex.from_product(
            [
                [
                    "players",
                    "games",
                    "wins",
                    "losses",
                    "ties",
                    "win_rate",
                    "tie_rate",
                    "decisive_games",
                    "decisive_win_rate",
                ],
                [False, True],
            ]
        ),
        fill_value=0,
    )
    report.columns = [
        f"{metric}_{'with_card' if present else 'without_card'}"
        for metric, present in report.columns
    ]
    report = report.reset_index()
    report["opponent_field_share"] = report["opponent"].map(
        grouped.drop_duplicates("opponent").set_index("opponent")[
            "opponent_field_share"
        ]
    )
    for presence in ("with_card", "without_card"):
        no_games = report[f"games_{presence}"] == 0
        report.loc[
            no_games,
            [
                f"win_rate_{presence}",
                f"tie_rate_{presence}",
                f"decisive_win_rate_{presence}",
            ],
        ] = float("nan")
    report["win_rate_delta"] = report["win_rate_with_card"] - report[
        "win_rate_without_card"
    ]
    report["match_point_delta"] = report["win_rate_delta"] * 3
    report["card_name"] = card_name
    report["archetype"] = archetype
    report["grouping"] = "variant" if use_variants else "archetype"

    round_group = (
        directed.groupby(["round", "card_present"], as_index=False)
        .agg(
            games=("match_result", "count"),
            players=("player_key", "nunique"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties=("ties", "sum"),
        )
    )
    round_group = add_rates(round_group)
    rounds = round_group.pivot(
        index="round",
        columns="card_present",
        values=["games", "players", "win_rate", "tie_rate", "decisive_win_rate"],
    ).reindex(
        columns=pd.MultiIndex.from_product(
            [["games", "players", "win_rate", "tie_rate", "decisive_win_rate"], [False, True]]
        ),
        fill_value=0,
    )
    rounds.columns = [
        f"{metric}_{'with_card' if present else 'without_card'}"
        for metric, present in rounds.columns
    ]
    rounds = rounds.reset_index()
    rounds["card_presence_rate"] = directed.groupby("round")["card_present"].mean().reindex(
        rounds["round"]
    ).to_numpy()
    rounds["win_rate_delta"] = rounds["win_rate_with_card"] - rounds[
        "win_rate_without_card"
    ]
    rounds["match_point_delta"] = rounds["win_rate_delta"] * 3

    total = directed.groupby("card_present", as_index=False).agg(
        games=("match_result", "count"),
        players=("player_key", "nunique"),
        wins=("wins", "sum"),
        losses=("losses", "sum"),
        ties=("ties", "sum"),
    )
    total = add_rates(total)
    total = total.set_index("card_present")
    weighted = report.dropna(subset=["win_rate_without_card", "win_rate_with_card"])
    weights = weighted["opponent_field_share"] / weighted["opponent_field_share"].sum()
    weighted_without = (weights * weighted["win_rate_without_card"]).sum()
    weighted_with = (weights * weighted["win_rate_with_card"]).sum()
    summary = pd.DataFrame(
        [
            {
                "archetype": archetype,
                "card_name": card_name,
                "tournaments": directed["tournament_id"].nunique(),
                "players_without_card": total.loc[False, "players"],
                "players_with_card": total.loc[True, "players"],
                "games_without_card": total.loc[False, "games"],
                "games_with_card": total.loc[True, "games"],
                "card_presence_rate": directed["card_present"].mean(),
                "win_rate_without_card": total.loc[False, "win_rate"],
                "win_rate_with_card": total.loc[True, "win_rate"],
                "win_rate_delta": total.loc[True, "win_rate"] - total.loc[False, "win_rate"],
                "field_weighted_win_rate_without_card": weighted_without,
                "field_weighted_win_rate_with_card": weighted_with,
                "field_weighted_delta": weighted_with - weighted_without,
                "tech_value_above_replacement": weighted_with - weighted_without,
                "match_point_delta_per_game": (weighted_with - weighted_without) * 3,
                "match_point_delta_per_100_games": (weighted_with - weighted_without) * 300,
            }
        ]
    )

    exposure = (
        directed.groupby(["round", "opponent"], as_index=False)
        .agg(
            games=("match_result", "count"),
            games_with_card=("card_present", "sum"),
            games_without_card=("card_present", lambda values: (~values).sum()),
        )
    )
    round_totals = exposure.groupby("round")["games"].sum().rename("round_games")
    exposure = exposure.merge(round_totals, on="round")
    exposure["opponent_field_share"] = exposure["games"] / exposure["round_games"]
    exposure["card_presence_rate"] = exposure["games_with_card"] / exposure["games"]

    field_rows = []
    for _, record in records.iterrows():
        for side in (1, 2):
            field_label = record[f"player{side}_{'variant' if use_variants else 'overall'}"]
            player_key = record[f"player{side}_key"]
            if pd.isna(field_label) or field_label == "Unknown" or pd.isna(player_key):
                continue
            field_rows.append(
                {
                    "tournament_id": record["tournament_id"],
                    "round": int(record["round_number"]),
                    "player_key": player_key,
                    "group": field_label,
                }
            )
    field = pd.DataFrame(field_rows).drop_duplicates(
        subset=["tournament_id", "round", "player_key"]
    )
    meta_share = (
        field.groupby(["round", "group"], as_index=False)
        .agg(players=("player_key", "nunique"))
    )
    field_totals = field.groupby("round")["player_key"].nunique().rename("total_players")
    meta_share = meta_share.merge(field_totals, on="round", how="left")
    meta_share["meta_share"] = meta_share["players"] / meta_share["total_players"]
    focal_field = (
        directed.groupby("round")["player_key"].nunique().rename("focal_players")
    )
    meta_share = meta_share.merge(focal_field, on="round", how="left")
    meta_share["archetype"] = archetype
    meta_share["card_name"] = card_name
    return {
        "summary": summary,
        "matchups": report.sort_values(
            "opponent_field_share", ascending=False
        ).reset_index(drop=True),
        "rounds": rounds.sort_values("round").reset_index(drop=True),
        "exposure": exposure.sort_values(["round", "games"], ascending=[True, False]).reset_index(drop=True),
        "meta_share": meta_share.sort_values(
            ["round", "meta_share", "group"], ascending=[True, False, True]
        ).reset_index(drop=True),
    }


def get_day_two_meta_share(
    tournament_id: str,
    division: str = "Masters",
    use_variants: bool = False,
) -> pd.DataFrame:
    """Return deck composition by round among Day 2 contenders.

    Each player's deck contributes at most once per round. The denominator is
    the number of players whose stored ``*_day_2_contention`` flag is true in
    that round, so the result describes the live Day 2 field rather than the
    composition of all pairing rows.
    """

    records = get_matchup_records(tournament_id, division)
    if records.empty:
        return pd.DataFrame()

    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    contender_frames = [
        records.loc[
            records["player1_day_2_contention"] == 1,
            ["round_number", "player1_key", label1],
        ]
        .dropna()
        .rename(columns={"player1_key": "player_key", label1: "group"}),
        records.loc[
            records["player2_day_2_contention"] == 1,
            ["round_number", "player2_key", label2],
        ]
        .dropna()
        .rename(columns={"player2_key": "player_key", label2: "group"}),
    ]
    contenders = pd.concat(contender_frames, ignore_index=True)
    contenders = contenders.drop_duplicates(
        subset=["round_number", "player_key"]
    )
    if contenders.empty:
        return pd.DataFrame()

    summary = (
        contenders.groupby(["round_number", "group"], as_index=False)
        .agg(players=("player_key", "nunique"))
    )
    totals = (
        contenders.groupby("round_number", as_index=False)
        .agg(total_day_2_contenders=("player_key", "nunique"))
    )
    summary = summary.merge(totals, on="round_number", how="left")
    summary["meta_share"] = (
        summary["players"] / summary["total_day_2_contenders"] * 100
    )
    summary["round"] = summary["round_number"]
    summary["grouping"] = "variant" if use_variants else "archetype"
    return summary[
        [
            "round",
            "group",
            "players",
            "total_day_2_contenders",
            "meta_share",
            "grouping",
        ]
    ].sort_values(
        ["round", "players", "group"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def get_day_two_meta_share_delta(
    tournament_id: str,
    start_round: int = 1,
    end_round: int = 8,
    division: str = "Masters",
    use_variants: bool = False,
) -> pd.DataFrame:
    """Compare Day 2 field composition between two rounds.

    ``delta_percentage_points`` is the later round's share minus the earlier
    round's share. Groups absent from either round are included with a zero
    share so emerging or eliminated archetypes remain visible.
    """

    if start_round < 1 or end_round < 1:
        raise ValueError("Round numbers must be positive.")
    if start_round == end_round:
        raise ValueError("Start and end rounds must be different.")

    meta_share = get_day_two_meta_share(
        tournament_id=tournament_id,
        division=division,
        use_variants=use_variants,
    )
    if meta_share.empty:
        return pd.DataFrame()

    selected = meta_share[meta_share["round"].isin([start_round, end_round])]
    if selected.empty:
        return pd.DataFrame()

    shares = selected.pivot_table(
        index="group",
        columns="round",
        values=["players", "total_day_2_contenders", "meta_share"],
        aggfunc="first",
        fill_value=0,
    )
    for metric in ("players", "total_day_2_contenders", "meta_share"):
        for round_number in (start_round, end_round):
            if (metric, round_number) not in shares:
                shares[(metric, round_number)] = 0

    report = pd.DataFrame(
        {
            "group": shares.index,
            "start_round": start_round,
            "end_round": end_round,
            "start_players": shares[("players", start_round)].astype(int),
            "end_players": shares[("players", end_round)].astype(int),
            "start_meta_share": shares[("meta_share", start_round)],
            "end_meta_share": shares[("meta_share", end_round)],
        }
    ).reset_index(drop=True)


def get_day_two_survival_curve(
    tournament_id: str,
    division: str = "Masters",
    use_variants: bool = False,
    max_round: int | None = None,
) -> pd.DataFrame:
    """Return round-by-round Day 2 survival and conversion metrics.

    ``conversion_rate`` is the share of an archetype's round-one contenders
    still contending in each later round. ``field_conversion_rate`` applies
    the same calculation to the entire Day 2-contending field. The
    ``survival_index`` compares those rates, where ``1.00x`` is average.
    """

    meta_share = get_day_two_meta_share(
        tournament_id=tournament_id,
        division=division,
        use_variants=use_variants,
    )
    if meta_share.empty:
        return pd.DataFrame()
    if max_round is not None:
        meta_share = meta_share[meta_share["round"] <= max_round].copy()
    if meta_share.empty:
        return pd.DataFrame()

    rounds = sorted(meta_share["round"].unique())
    groups = sorted(meta_share["group"].unique())
    grid = pd.MultiIndex.from_product(
        [rounds, groups], names=["round", "group"]
    ).to_frame(index=False)
    report = grid.merge(
        meta_share[
            [
                "round",
                "group",
                "players",
                "total_day_2_contenders",
                "meta_share",
            ]
        ],
        on=["round", "group"],
        how="left",
    )
    report["players"] = report["players"].fillna(0).astype(int)
    report["meta_share"] = report["meta_share"].fillna(0.0)
    report["total_day_2_contenders"] = (
        report.groupby("round")["total_day_2_contenders"]
        .transform("first")
        .fillna(0)
        .astype(int)
    )

    first_round = min(rounds)
    start_players = report.loc[
        report["round"] == first_round,
        ["group", "players"],
    ].rename(columns={"players": "start_players"})
    start_total = int(
        report.loc[
            report["round"] == first_round,
            "total_day_2_contenders",
        ].iloc[0]
    )
    report = report.merge(start_players, on="group", how="left")
    report["conversion_rate"] = (
        report["players"] / report["start_players"].where(
            report["start_players"] > 0
        ) * 100
    )
    report["field_conversion_rate"] = (
        report["total_day_2_contenders"] / start_total * 100
        if start_total
        else pd.NA
    )
    report["survival_index"] = (
        report["conversion_rate"]
        / report["field_conversion_rate"].where(
            report["field_conversion_rate"] > 0
        )
    )
    report["grouping"] = "variant" if use_variants else "archetype"
    return (
        report[
            [
                "round",
                "group",
                "players",
                "start_players",
                "conversion_rate",
                "total_day_2_contenders",
                "field_conversion_rate",
                "survival_index",
                "meta_share",
                "grouping",
            ]
        ]
        .sort_values(
            ["round", "survival_index", "group"],
            ascending=[True, False, True],
        )
        .reset_index(drop=True)
    )
    report["delta_percentage_points"] = (
        report["end_meta_share"] - report["start_meta_share"]
    )
    report["grouping"] = "variant" if use_variants else "archetype"
    return report.sort_values(
        ["delta_percentage_points", "end_meta_share", "group"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def get_archetype_round_performance(
    tournament_id: str,
    division: str = "Masters",
    use_variants: bool = False,
    include_unknown: bool = False,
    day_2_contention: bool | None = None,
    max_round: int | None = None,
) -> pd.DataFrame:
    """Return overall archetype performance separately for each round.

    Day 2 contention is evaluated for the opposing player, matching the
    perspective used by ``get_matchup_round_cohorts``. When no contention
    filter is supplied, each round includes an ``all`` row plus yes/no rows
    where the tournament's Day 2 rule applies.
    """

    records = get_matchup_records(tournament_id, division)
    if records.empty:
        return pd.DataFrame()
    if max_round is not None:
        records = records[records["round_number"] <= max_round].copy()

    label1 = "player1_variant" if use_variants else "player1_overall"
    label2 = "player2_variant" if use_variants else "player2_overall"
    records = records.dropna(subset=[label1, label2]).copy()
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()
    if records.empty:
        return pd.DataFrame()

    directed_frames = []
    for _, record in records.iterrows():
        round_number = int(record["round_number"])
        p1_contention = bool(record["player1_day_2_contention"])
        p2_contention = bool(record["player2_day_2_contention"])
        directed_frames.extend(
            [
                {
                    "round": round_number,
                    "archetype": record[label1],
                    "day_2_contender": p1_contention,
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player1_win"),
                    "losses": int(record["match_result"] == "player2_win"),
                },
                {
                    "round": round_number,
                    "archetype": record[label2],
                    "day_2_contender": p2_contention,
                    "match_result": record["match_result"],
                    "wins": int(record["match_result"] == "player2_win"),
                    "losses": int(record["match_result"] == "player1_win"),
                },
            ]
        )

    directed = pd.DataFrame(directed_frames)
    if directed.empty:
        return pd.DataFrame()
    if day_2_contention is not None:
        directed = directed[
            directed["day_2_contender"] == day_2_contention
        ].copy()
    if directed.empty:
        return pd.DataFrame()

    summary = (
        directed.groupby(["round", "archetype", "day_2_contender"], as_index=False)
        .agg(
            games=("match_result", "count"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("match_result", _count_ties),
        )
    )
    _add_win_rates(summary)
    summary["day_2_contention"] = summary["day_2_contender"].map(
        {True: "yes", False: "no"}
    ).fillna("not_applicable")

    if day_2_contention is None:
        all_summary = (
            directed.groupby(["round", "archetype"], as_index=False)
            .agg(
                games=("match_result", "count"),
                wins=("wins", "sum"),
                losses=("losses", "sum"),
                ties_or_unknown=("match_result", _count_ties),
            )
        )
        _add_win_rates(all_summary)
        all_summary["day_2_contention"] = "all"
        summary = pd.concat([summary, all_summary], ignore_index=True)

    status_order = {"all": 0, "yes": 1, "no": 2, "not_applicable": 3}
    totals = (
        summary.groupby(["archetype", "day_2_contention"], as_index=False)
        .agg(
            games=("games", "sum"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties_or_unknown=("ties_or_unknown", "sum"),
        )
    )
    _add_win_rates(totals)
    totals["round"] = "TOTAL"
    summary = pd.concat([summary, totals], ignore_index=True)
    summary["_status_order"] = summary["day_2_contention"].map(status_order)
    summary["_round_order"] = summary["round"].map(
        lambda value: 10**9 if value == "TOTAL" else int(value)
    )
    return summary.sort_values(
        ["_round_order", "archetype", "_status_order"],
        ascending=[True, True, True],
    ).drop(
        columns=["_status_order", "_round_order", "day_2_contender"],
    ).reset_index(drop=True)
