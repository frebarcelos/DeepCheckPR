"""Pure transformation functions for aggregating PR data using reductions."""

from collections.abc import Iterable
from functools import reduce

from pr_analyzer.io.csv_reader import PRRecord


def count_by_language(prs: Iterable[PRRecord]) -> dict[str, int]:
    """
    Counts the number of PRs per language using a pure reduction.
    Returns a dictionary mapping language names to counts.
    """
    return reduce(
        lambda acc, pr: acc | {pr.language: acc.get(pr.language, 0) + 1},
        prs,
        {},
    )
