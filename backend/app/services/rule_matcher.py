from collections.abc import Iterable

from app.models.rule import Rule


def normalize_match_text(value: str) -> str:
    """Normalize text for case-insensitive substring matching."""
    return value.casefold()


def matching_rules(rules: Iterable[Rule], comment_text: str | None) -> list[Rule]:
    """Return every active rule whose keyword occurs anywhere in the comment."""
    if not comment_text:
        return []

    normalized_comment = normalize_match_text(comment_text)
    return [
        rule
        for rule in rules
        if rule.active
        and normalize_match_text(rule.keyword.strip()) in normalized_comment
    ]
