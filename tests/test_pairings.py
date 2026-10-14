"""Tests for the RK9 pairing parser."""

from bs4 import BeautifulSoup

from src.pairings import (
    get_division_rounds,
    normalize_player_name,
    parse_round_fragment,
    resolve_player,
)


def test_get_division_rounds_reads_rk9_tabs():
    soup = BeautifulSoup(
        """
        <a id="P2-tab" role="tab">Masters in Round 16</a>
        <a id="P2R1-tab" role="tab">R1</a>
        <a id="P2R16-tab" role="tab">R16</a>
        <a id="P9-tab" role="tab">Senior in Round 14</a>
        <a id="P9R1-tab" role="tab">R1</a>
        """,
        "lxml",
    )

    assert get_division_rounds(soup) == {
        "Masters": (2, (1, 16)),
        "Senior": (9, (1,)),
    }


def test_parse_round_fragment_preserves_result_and_table():
    soup = BeautifulSoup(
        """
        <div class="row match complete">
          <div class="player player1 winner">
            <span class="name">Riley<br>McKay [CA]<br></span>
            <span class="record" data-wins="1" data-losses="0" data-ties="0">(1-0-0)</span>
            3 pts
          </div>
          <div class="tablenumber"> 865 </div>
          <div class="player player2 loser">
            <span class="name">Austin<br>Charles [US]<br></span>
            <span class="record" data-wins="0" data-losses="1" data-ties="0">(0-1-0)</span>
            0 pts
          </div>
        </div>
        """,
        "lxml",
    )

    matches = parse_round_fragment(soup, "event", "Masters", 2, 1)

    assert len(matches) == 1
    assert matches[0].table_number == 865
    assert matches[0].status == "complete"
    assert matches[0].player1.outcome == "win"
    assert matches[0].player2.outcome == "loss"


def test_name_resolution_does_not_guess_duplicates():
    player = type(
        "Player",
        (),
        {
            "first_name": "Jose",
            "last_name": "López",
            "country": "ES",
            "record": None,
            "points": None,
            "outcome": "tie_or_unknown",
        },
    )()
    roster = [
        {"first_name": "Jose", "last_name": "López", "country": "ES", "player_key": "a"},
        {"first_name": "Jose", "last_name": "López", "country": "ES", "player_key": "b"},
    ]

    assert normalize_player_name("Jose", "López") == "jose lópez"
    assert resolve_player(player, roster).status == "ambiguous"
