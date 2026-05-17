"""Pure transformation functions for aggregating PR data using reductions."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import reduce
from typing import Any

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.mappers import PRStats


@dataclass
class EnrichedPR:
    pr: PRRecord
    project_type: str
    contribution_nature: str
    description_clarity: str


def count_by_field(field: str) -> Callable[[Iterable[Any]], dict[str, int]]:
    return lambda items: reduce(
        lambda acc, item: acc
        | {getattr(item, field): acc.get(getattr(item, field), 0) + 1},
        items,
        {},
    )


def count_by_language(prs: Iterable[PRRecord]) -> dict[str, int]:
    """
    Counts the number of PRs per language using a pure reduction.
    Returns a dictionary mapping language names to counts.
    """
    return count_by_field("language")(prs)


def count_by_project_type(enriched_prs: Iterable[EnrichedPR]) -> dict[str, int]:
    """
    Counts the number of PRs per project type.
    """
    return count_by_field("project_type")(enriched_prs)


def accumulate_stats(stats: Iterable[PRStats]) -> dict[str, int]:
    """
    Accumulates totals and count for a collection of PRStats in a single pass.
    """
    return reduce(
        lambda acc, stat: {
            "chars": stat.body_char_count + acc["chars"],
            "words": stat.body_word_count + acc["words"],
            "changes": stat.total_changes + acc["changes"],
            "merges": int(stat.is_merged) + acc["merges"],
            "count": acc["count"] + 1,
        },
        stats,
        {"chars": 0, "words": 0, "changes": 0, "merges": 0, "count": 0},
    )


def aggregate_stats(stats: Iterable[PRStats]) -> dict[str, float]:
    """
    Computes average statistics for a collection of PRStats.
    Returns a dict with avg_chars, avg_words, avg_changes, and merge_rate.
    """
    acc = accumulate_stats(stats)
    count = acc["count"]

    if count == 0:
        return {
            "avg_chars": 0.0,
            "avg_words": 0.0,
            "avg_changes": 0.0,
            "merge_rate": 0.0,
        }

    return {
        "avg_chars": acc["chars"] / count,
        "avg_words": acc["words"] / count,
        "avg_changes": acc["changes"] / count,
        "merge_rate": acc["merges"] / count,
    }
