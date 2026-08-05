"""
Deck archetype classifier.
"""

from collections import Counter

from src.metadata import load_archetypes
from src.models import (
    RuleResult,
    ClassificationResult,
)


def count_cards(cards):
    """
    Count copies of each card in a deck.
    """

    counts = Counter()

    for card in cards:
        counts[card.card_name] += card.quantity

    return counts


def evaluate_rule(card_count, operator, value):
    """
    Evaluate one archetype rule.
    """

    if operator == ">=":
        return card_count >= value

    if operator == ">":
        return card_count > value

    if operator == "<=":
        return card_count <= value

    if operator == "<":
        return card_count < value

    if operator == "=":
        return card_count == value

    raise ValueError(f"Unknown operator: {operator}")


def classify_deck(cards):
    """
    Classify a deck into the best matching archetype.
    """

    rules = load_archetypes()

    card_counts = count_cards(cards)

    best_match = None
    best_partial = None

    for priority in sorted(rules["priority"].unique()):

        priority_rules = rules[
            rules["priority"] == priority
        ]

        for (overall, variant), group in priority_rules.groupby(
            ["overall_archetype", "variant"]
        ):

            passed_rules = 0
            rule_results = []

            for _, rule in group.iterrows():

                actual = card_counts.get(
                    rule["card_name"],
                    0,
                )

                passed = evaluate_rule(
                    actual,
                    rule["operator"],
                    rule["value"],
                )

                if passed:
                    passed_rules += 1

                rule_results.append(
                    RuleResult(
                        card_name=rule["card_name"],
                        operator=rule["operator"],
                        expected=rule["value"],
                        actual=actual,
                        passed=passed,
                    )
                )

            score = passed_rules / len(group)

            result = ClassificationResult(
                overall=overall,
                variant=variant,
                matched=(score == 1.0),
                priority=priority,
                score=score,
                rule_results=rule_results,
                core_pokemon=[],
                core_trainers=[],
            )

            if result.matched:

                if (
                    best_match is None
                    or result.priority < best_match.priority
                ):
                    best_match = result

            else:

                if (
                    best_partial is None
                    or result.score > best_partial.score
                    or (
                        result.score == best_partial.score
                        and result.priority < best_partial.priority
                    )
                ):
                    best_partial = result

    if best_match is not None:
        return best_match

    if (
        best_partial is not None
        and best_partial.score > 0
    ):
        return best_partial

    return ClassificationResult(
        overall="Unknown",
        variant="Unknown",
        matched=False,
        priority=None,
        score=0.0,
        rule_results=[],
        core_pokemon=[],
        core_trainers=[],
    )