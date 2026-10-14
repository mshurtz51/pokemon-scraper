"""Build and summarize matchup records from RK9 pairings and deck data."""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.config import DATABASE_NAME, PAIRING_DATABASE_NAME


MATCHUP_COLUMNS = (
    "match_key, tournament_id, division, pod, round_number, table_number, "
    "status, player1_key, player2_key, player1_deck_url, player2_deck_url, "
    "player1_outcome, player2_outcome, player1_record, player2_record, "
    "player1_points_after, player2_points_after, player1_points_before, "
    "player2_points_before, player1_overall, player1_variant, player2_overall, "
    "player2_variant, match_result, eligible_for_analytics"
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
    CASE
        WHEN m.player1_outcome = 'win'
            AND m.player2_outcome = 'loss'
            THEN 'player1_win'
        WHEN m.player1_outcome = 'loss'
            AND m.player2_outcome = 'win'
            THEN 'player2_win'
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
    return "tie_or_unknown"


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
                match_result,
                eligible,
            )
        )

    conn.executemany(
        f"INSERT OR REPLACE INTO matchup_records ({MATCHUP_COLUMNS}) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
    summary["a_win_rate"] = summary["a_wins"] / decisive
    summary["b_win_rate"] = summary["b_wins"] / decisive
    summary.loc[summary["is_mirror"], ["a_win_rate", "b_win_rate"]] = pd.NA
    return summary.sort_values(["games", "archetype_a", "archetype_b"], ascending=[False, True, True])


def get_archetype_matchup_matrix(
    tournament_id: str | None = None,
    division: str = "Masters",
    use_variants: bool = False,
    include_unknown: bool = False,
) -> pd.DataFrame:
    """Return a directed archetype win-rate matrix.

    Rows are the focal archetype and columns are opposing archetypes. Values
    are decisive-game win rates, so ties and unknown outcomes are excluded
    from each cell's denominator. Mirror cells represent the archetype's
    combined win rate across both sides of the mirror.
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
            ),
            records[[label2, label1, "match_result"]].rename(
                columns={label2: "archetype", label1: "opponent"}
            ).assign(
                wins=lambda frame: (frame["match_result"] == "player2_win").astype(int),
                losses=lambda frame: (frame["match_result"] == "player1_win").astype(int),
            ),
        ],
        ignore_index=True,
    )
    summary = (
        directed.groupby(["archetype", "opponent"], as_index=False)
        .agg(
            wins=("wins", "sum"),
            losses=("losses", "sum"),
        )
    )
    decisive = summary["wins"] + summary["losses"]
    summary["games"] = decisive
    summary["win_rate"] = summary["wins"] / decisive.where(decisive > 0)
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
        )
    )
    summary["ties_or_unknown"] = (
        summary["games"] - summary["wins"] - summary["losses"]
    )
    summary["decisive_games"] = summary["wins"] + summary["losses"]
    summary["win_rate"] = summary["wins"] / summary["decisive_games"].where(
        summary["decisive_games"] > 0
    )
    return summary.sort_values(
        ["tournament_id", "games", "archetype", "opponent"],
        ascending=[True, False, True, True],
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
        )
    )
    summary["ties_or_unknown"] = (
        summary["games"] - summary["wins"] - summary["losses"]
    )
    summary["decisive_games"] = summary["wins"] + summary["losses"]
    summary["win_rate"] = summary["wins"] / summary["decisive_games"].where(
        summary["decisive_games"] > 0
    )
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
    points_before: float,
    round_number: int,
    rule: tuple[int, int] | None,
) -> bool | None:
    """Determine whether a player can still reach the Day 2 threshold."""

    if rule is None:
        return None
    phase_one_rounds, threshold = rule
    remaining_rounds = max(phase_one_rounds - round_number + 1, 0)
    return points_before + (remaining_rounds * 3) >= threshold


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
            "player1_points_before",
            "player2_points_before",
        ]
    ).copy()
    if max_round is not None:
        records = records[records["round_number"] <= max_round]
    if not include_unknown:
        records = records[
            (records[label1] != "Unknown")
            & (records[label2] != "Unknown")
        ].copy()

    field_sizes = _division_player_counts()
    directed_frames = []
    for _, record in records.iterrows():
        rule = _day_two_rule(
            field_sizes.get((record["tournament_id"], division), 0)
        )
        round_number = int(record["round_number"])
        p1_contention = _is_day_two_contender(
            record["player1_points_before"], round_number, rule
        )
        p2_contention = _is_day_two_contender(
            record["player2_points_before"], round_number, rule
        )
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
        )
    )
    summary["ties_or_unknown"] = (
        summary["games"] - summary["wins"] - summary["losses"]
    )
    summary["decisive_games"] = summary["wins"] + summary["losses"]
    summary["win_rate"] = summary["wins"] / summary["decisive_games"].where(
        summary["decisive_games"] > 0
    )
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
            )
        )
        all_summary["ties_or_unknown"] = (
            all_summary["games"]
            - all_summary["wins"]
            - all_summary["losses"]
        )
        all_summary["decisive_games"] = (
            all_summary["wins"] + all_summary["losses"]
        )
        all_summary["win_rate"] = all_summary["wins"] / all_summary[
            "decisive_games"
        ].where(all_summary["decisive_games"] > 0)
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
    """Return cumulative matchup win rates with rounds as the index."""

    cohorts = get_matchup_round_cohorts(**kwargs)
    if cohorts.empty:
        return pd.DataFrame()
    grouped = (
        cohorts.groupby(["round", "matchup"], as_index=False)
        .agg(
            wins=("wins", "sum"),
            losses=("losses", "sum"),
        )
    )
    decisive = grouped["wins"] + grouped["losses"]
    grouped["win_rate"] = grouped["wins"] / decisive.where(decisive > 0)
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
    totals["decisive_games"] = totals["wins"] + totals["losses"]
    totals["win_rate"] = totals["wins"] / totals["decisive_games"].where(
        totals["decisive_games"] > 0
    )
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
        )
    )
    summary["ties_or_unknown"] = (
        summary["games"] - summary["wins"] - summary["losses"]
    )
    summary["decisive_games"] = summary["wins"] + summary["losses"]
    summary["win_rate"] = summary["wins"] / summary["decisive_games"].where(
        summary["decisive_games"] > 0
    )
    return summary.sort_values(
        ["win_rate", "games", "archetype"],
        ascending=[False, False, True],
        na_position="last",
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

    field_size = _division_player_counts().get((tournament_id, division), 0)
    rule = _day_two_rule(field_size)
    directed_frames = []
    for _, record in records.iterrows():
        round_number = int(record["round_number"])
        p1_contention = _is_day_two_contender(
            record["player1_points_before"], round_number, rule
        )
        p2_contention = _is_day_two_contender(
            record["player2_points_before"], round_number, rule
        )
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
        )
    )
    summary["ties_or_unknown"] = (
        summary["games"] - summary["wins"] - summary["losses"]
    )
    summary["decisive_games"] = summary["wins"] + summary["losses"]
    summary["win_rate"] = summary["wins"] / summary["decisive_games"].where(
        summary["decisive_games"] > 0
    )
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
            )
        )
        all_summary["ties_or_unknown"] = (
            all_summary["games"]
            - all_summary["wins"]
            - all_summary["losses"]
        )
        all_summary["decisive_games"] = (
            all_summary["wins"] + all_summary["losses"]
        )
        all_summary["win_rate"] = all_summary["wins"] / all_summary[
            "decisive_games"
        ].where(all_summary["decisive_games"] > 0)
        all_summary["day_2_contention"] = "all"
        summary = pd.concat([summary, all_summary], ignore_index=True)

    status_order = {"all": 0, "yes": 1, "no": 2, "not_applicable": 3}
    summary["_status_order"] = summary["day_2_contention"].map(status_order)
    return summary.sort_values(
        ["round", "archetype", "_status_order"],
        ascending=[True, True, True],
    ).drop(columns=["_status_order", "day_2_contender"]).reset_index(drop=True)
