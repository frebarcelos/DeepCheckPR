"""Pure transformation functions for mapping PR records to metadata and stats."""

from typing import NamedTuple

from pr_analyzer.io.csv_reader import PRRecord


class PRStats(NamedTuple):
    """Statistics for a single Pull Request record."""

    body_char_count: int
    body_word_count: int
    total_changes: int
    is_merged: bool


def compute_stats(pr: PRRecord) -> PRStats:
    """
    Computes statistics for a given PR record.
    Returns a PRStats named tuple containing character count, word count,
    total changes (additions + deletions), and a boolean indicating if it was merged.
    """
    body_char_count = len(pr.body)
    body_word_count = len(pr.body.split())

    total_changes = pr.additions + pr.deletions
    is_merged = bool(pr.merged_at)

    return PRStats(
        body_char_count=body_char_count,
        body_word_count=body_word_count,
        total_changes=total_changes,
        is_merged=is_merged,
    )
