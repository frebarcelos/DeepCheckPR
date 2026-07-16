"""
distributions.py — Local fallback for the count_by_* reducers expected from
`pr_analyzer.transforms.reducers`.

Mirrors the reducers API so the UI can render distribution charts when the
main implementation is unavailable.

These helpers are pure (no I/O, no global state) even though they live in
the UI tree, which keeps the contract identical to the future pure module.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import reduce
from typing import Any


def count_by_field(field: str) -> Callable[[Iterable[Any]], dict[str, int]]:
    """HOF: returns a reducer that counts occurrences of `field` on each item.

    Matches the reducers signature. Works on either a NamedTuple (PRRecord-like)
    or a Mapping — the bridge tolerates both representations.
    """

    def _value(item: Any) -> str:
        if hasattr(item, field):
            raw = getattr(item, field)
        elif isinstance(item, dict):
            raw = item.get(field, "")
        else:
            raw = ""
        return str(raw).strip() or "—"

    def _reducer(items: Iterable[Any]) -> dict[str, int]:
        return reduce(
            lambda acc, item: acc | {_value(item): acc.get(_value(item), 0) + 1},
            items,
            {},
        )

    return _reducer


count_by_language: Callable[[Iterable[Any]], dict[str, int]] = count_by_field(
    "language"
)
count_by_project_type: Callable[[Iterable[Any]], dict[str, int]] = count_by_field(
    "project_type"
)
count_by_contribution_nature: Callable[[Iterable[Any]], dict[str, int]] = (
    count_by_field("contribution_nature")
)
count_by_description_clarity: Callable[[Iterable[Any]], dict[str, int]] = (
    count_by_field("description_clarity")
)


def count_from_dataframe_column(values: Iterable[Any]) -> dict[str, int]:
    """Reducer over a plain iterable of pre-extracted column values."""
    return reduce(
        lambda acc, v: acc | {str(v): acc.get(str(v), 0) + 1},
        (v for v in values if v is not None and str(v).strip() != ""),
        {},
    )
