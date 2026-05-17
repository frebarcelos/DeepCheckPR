"""Pure transformation functions: filters, mappers, and reducers."""

from pr_analyzer.transforms.filters import (
    by_date_range,
    by_language,
    by_state,
    combine_filters,
    with_min_size,
    with_non_empty_body,
)
from pr_analyzer.transforms.mappers import PRStats, compute_stats
from pr_analyzer.transforms.reducers import (
    EnrichedPR,
    accumulate_stats,
    aggregate_stats,
    count_by_field,
    count_by_language,
    count_by_project_type,
)

__all__ = (
    "by_state",
    "by_language",
    "by_date_range",
    "with_non_empty_body",
    "with_min_size",
    "combine_filters",
    "PRStats",
    "compute_stats",
    "count_by_language",
    "count_by_field",
    "count_by_project_type",
    "EnrichedPR",
    "accumulate_stats",
    "aggregate_stats",
)
