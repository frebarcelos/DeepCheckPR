"""CSV readers and schema normalization for GitHub pull request records."""

import csv
from collections.abc import Generator, Mapping
from typing import NamedTuple


class PRRecord(NamedTuple):
    """Immutable pull request record normalized from the Kaggle CSV dataset."""

    pr_id: int | None
    repo_name: str
    language: str
    title: str
    body: str
    state: str
    created_at: str
    merged_at: str
    additions: int | None
    deletions: int | None
    changed_files: int | None


def _text(raw_row: Mapping[str, object], field: str) -> str:
    value = raw_row.get(field, "")
    return "" if value is None else str(value).strip()


def _integer(raw_row: Mapping[str, object], field: str) -> int | None:
    try:
        return int(_text(raw_row, field))
    except ValueError:
        return None


def read_csv_lazy(filepath: str) -> Generator[dict[str, str], None, None]:
    """Yield raw CSV rows lazily without loading the whole file into memory."""
    with open(filepath, encoding="utf-8", newline="") as csv_file:
        yield from csv.DictReader(csv_file)


def apply_schema(raw_row: Mapping[str, object]) -> PRRecord:
    """Convert a raw CSV row into an immutable, typed PRRecord."""
    return PRRecord(
        pr_id=_integer(raw_row, "pr_id"),
        repo_name=_text(raw_row, "repo_name"),
        language=_text(raw_row, "language").lower(),
        title=_text(raw_row, "title"),
        body=_text(raw_row, "body"),
        state=_text(raw_row, "state").lower(),
        created_at=_text(raw_row, "created_at"),
        merged_at=_text(raw_row, "merged_at"),
        additions=_integer(raw_row, "additions"),
        deletions=_integer(raw_row, "deletions"),
        changed_files=_integer(raw_row, "changed_files"),
    )


def read_prs(filepath: str) -> Generator[PRRecord, None, None]:
    """Yield normalized pull request records from a CSV file."""
    return (apply_schema(row) for row in read_csv_lazy(filepath))
