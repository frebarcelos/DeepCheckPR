from collections.abc import Callable
from typing import Any


def by_state(state: str) -> Callable[[Any], bool]:
    """
    Returns a predicate that checks if a PR's state matches the given state.
    The comparison is case-insensitive.
    """
    target_state = state.lower()

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "state") or pr.state is None:
            return False
        return str(pr.state).lower() == target_state

    return predicate


def by_language(language: str) -> Callable[[Any], bool]:
    """
    Returns a predicate that checks if a PR's language matches the given language.
    The comparison is case-insensitive.
    """
    target_language = language.lower()

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "language") or pr.language is None:
            return False
        return str(pr.language).lower() == target_language

    return predicate


def by_date_range(start: str, end: str) -> Callable[[Any], bool]:
    """
    Returns a predicate that checks if a PR's created_at date falls within
    the given start and end dates (inclusive). Expects ISO 8601 strings.
    """

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "created_at") or pr.created_at is None:
            return False
        pr_date = str(pr.created_at)[:10]
        return start <= pr_date <= end

    return predicate


def with_non_empty_body() -> Callable[[Any], bool]:
    """
    Returns a predicate that checks if a PR has a non-empty body.
    """

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "body") or pr.body is None:
            return False
        return str(pr.body).strip() != ""

    return predicate


def with_min_size(min_changes: int) -> Callable[[Any], bool]:
    """
    Returns a predicate that checks if the total size (additions + deletions)
    of a PR is greater than or equal to min_changes.
    """

    def predicate(pr: Any) -> bool:
        additions = getattr(pr, "additions", 0) or 0
        deletions = getattr(pr, "deletions", 0) or 0
        try:
            return (int(additions) + int(deletions)) >= min_changes
        except (ValueError, TypeError):
            return False

    return predicate


def combine_filters(*predicates: Callable[[Any], bool]) -> Callable[[Any], bool]:
    """
    Combines multiple predicates using the logical AND (all).
    If no predicates are provided, returns True for any PR.
    """

    def predicate(pr: Any) -> bool:
        return all(p(pr) for p in predicates)

    return predicate
