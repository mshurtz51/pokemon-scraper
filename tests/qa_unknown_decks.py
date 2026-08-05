"""
Generate a deck classification QA report.
"""

import pandas as pd

from src.classifier import classify_deck
from src.config import EXPORT_FOLDER
from src.queries import (
    get_players,
    get_deck,
)


def core_cards(cards, card_type, minimum=2):
    """
    Return cards appearing at least 'minimum' times.
    """

    core = []

    for card in cards:

        if (
            card.card_type == card_type
            and card.quantity >= minimum
        ):
            core.append(card)

    core.sort(
        key=lambda x: (-x.quantity, x.card_name)
    )

    return ", ".join(
        f"{card.quantity}x {card.card_name}"
        for card in core
    )


def failed_rules(rule_results):
    """
    Return a readable summary of failed rules.
    """

    failed = []

    for rule in rule_results:

        if not rule.passed:

            failed.append(
                f"{rule.card_name} {rule.operator} {rule.expected} "
                f"(Found: {rule.actual})"
            )

    return " | ".join(failed)


def main():

    report = []

    players = get_players()

    total = len(players)

    for i, player in enumerate(players, start=1):

        player_key = player[0]
        tournament_id = player[1]
        first_name = player[2]
        last_name = player[3]
        standing = player[4]

        print(f"{i}/{total}")

        cards = get_deck(player_key)

        result = classify_deck(cards)

        report.append({

            "tournament": tournament_id,
            "standing": standing,
            "player": f"{first_name} {last_name}",

            "overall": result.overall,
            "variant": result.variant,

            "matched": result.matched,
            "score": result.score,

            "failed_rules": failed_rules(
                result.rule_results
            ),

            "core_pokemon": core_cards(
                cards,
                "pokemon",
            ),

            "core_trainers": core_cards(
                cards,
                "trainer",
            ),

        })

    df = pd.DataFrame(report)

    false_matches = df[
        df["matched"] == False
    ].copy()

    summary = (
        false_matches
        .groupby("overall")
        .size()
        .reset_index(name="count")
        .sort_values(
            "count",
            ascending=False,
        )
    )

    print()
    print("=" * 60)
    print("CLASSIFICATION QA")
    print("=" * 60)
    print()

    print(f"Total decks      : {len(df)}")
    print(f"Matched          : {df['matched'].sum()}")
    print(f"False matches    : {len(false_matches)}")

    print()
    print("False Matches by Overall")
    print("-" * 60)

    print(summary.to_string(index=False))

    output = EXPORT_FOLDER / "deck_classification_report.xlsx"

    with pd.ExcelWriter(output) as writer:

        summary.to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )

        df.to_excel(
            writer,
            sheet_name="All Decks",
            index=False,
        )

        false_matches.to_excel(
            writer,
            sheet_name="False Matches",
            index=False,
        )

    print()
    print(f"Saved report to:\n{output}")


if __name__ == "__main__":
    main()