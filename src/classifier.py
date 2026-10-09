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


def prepare_rules(rules):
    """Compile the metadata rule table for repeated deck classification."""

    compiled = []

    for priority in sorted(rules["priority"].unique()):
        priority_rules = rules[rules["priority"] == priority]

        for (overall, variant), group in priority_rules.groupby(
            ["overall_archetype", "variant"]
        ):
            checks = [
                (row["card_name"], row["operator"], row["value"])
                for _, row in group.iterrows()
            ]
            compiled.append((priority, overall, variant, checks))

    return compiled


def classify_deck(cards, rules=None):
    """
    Classify a deck into the best matching archetype.
    """

    if rules is None:
        rules = prepare_rules(load_archetypes())

    card_counts = count_cards(cards)

    best_match = None
    best_partial = None

    for priority, overall, variant, checks in rules:

            passed_rules = 0
            rule_results = []

            for card_name, operator, value in checks:
                actual = card_counts.get(
                    card_name,
                    0,
                )

                passed = evaluate_rule(
                    actual,
                    operator,
                    value,
                )

                if passed:
                    passed_rules += 1

                rule_results.append(
                    RuleResult(
                        card_name=card_name,
                        operator=operator,
                        expected=value,
                        actual=actual,
                        passed=passed,
                    )
                )

            score = passed_rules / len(checks)

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

    #
    # Perfect match
    #

    if best_match is not None:
        return best_match

    #
    # Partial match -> Unknown
    #

    if best_partial is not None:

        return ClassificationResult(
            overall="Unknown",
            variant="Unknown",
            matched=False,
            priority=None,
            score=best_partial.score,
            rule_results=best_partial.rule_results,
            core_pokemon=[],
            core_trainers=[],
        )

    #
    # No match at all
    #

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
