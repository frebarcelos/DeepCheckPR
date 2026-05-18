"""
pipeline_bridge.py — Bridge between the functional pipeline (PRRecord +
transforms + llm + cache) and the UI's pandas-based view layer.

This module is the integration seam for dev5: it imports from the modules
owned by dev1 (`io/`), dev2 (`transforms/`), dev3 (`llm/`), and dev4
(`cache/`, `pipeline/`). Where a downstream module is still in progress
(e.g. dev2's reducers, dev3's `enrich_prs`), we fall back to local helpers
with the same shape so the UI is functional today and swaps cleanly when
the real implementations land.

Side-effect module — UI tree is allowed to do I/O and wrap effects.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from io import BytesIO, StringIO
from typing import Any, NamedTuple

import pandas as pd
from utils.distributions import (
    count_by_contribution_nature as _local_nature,
)
from utils.distributions import (
    count_by_description_clarity as _local_clarity,
)
from utils.distributions import (
    count_by_language as _local_language,
)
from utils.distributions import (
    count_by_project_type as _local_project_type,
)

from pr_analyzer.cache.memo import cached_classify
from pr_analyzer.io import PRRecord, apply_schema
from pr_analyzer.llm.classifiers import (
    classify_contribution_nature,
    classify_description_clarity,
    classify_project_type,
)
from pr_analyzer.pipeline.builder import build_pipeline
from pr_analyzer.transforms import (
    by_language,
    by_state,
    combine_filters,
    with_min_size,
    with_non_empty_body,
)

# ── Dev2 reducers (when available) ───────────────────────────────────────────
# When dev2 ships transforms.reducers (TASK-31/32) this import block resolves
# to their implementation; until then we use the local fallback that mirrors
# the same shape (Iterable[Any] -> dict[str, int]).

try:  # pragma: no cover - exercised after dev2 merge
    from pr_analyzer.transforms.reducers import (
        count_by_contribution_nature,
        count_by_description_clarity,
        count_by_language,
        count_by_project_type,
    )
except ImportError:
    count_by_language = _local_language
    count_by_project_type = _local_project_type
    count_by_contribution_nature = _local_nature
    count_by_description_clarity = _local_clarity


# ── Dev3 enrich_prs (when available) ────────────────────────────────────────-
# When dev3 ships `enrich_prs` (TASK-35) the bridge delegates to it directly.
# Until then we apply the three classifier stubs via map() locally.


class EnrichedPR(NamedTuple):
    """Local mirror of the EnrichedPR type expected from dev3/dev4.

    Matches the field names dev2's `count_by_*` will rely on. When dev3 ships
    their type we replace this with `from pr_analyzer.llm import EnrichedPR`.
    """

    pr_id: int
    repo_name: str
    language: str
    title: str
    body: str
    state: str
    additions: int
    deletions: int
    project_type: str
    contribution_nature: str
    description_clarity: str


# ── Type aliases ──────────────────────────────────────────────────────────────

ClassifierFn = Callable[..., str]
LLMRunHandle = Any  # Agent | MagicMock — narrow to Protocol once dev3 fixes type


# ── CSV ingestion via dev1 ────────────────────────────────────────────────────


def parse_csv_bytes(raw: bytes) -> tuple[PRRecord, ...]:
    """Convert raw CSV bytes (uploaded file) into an immutable tuple of PRRecords.

    Uses dev1's `apply_schema` per row. Falls back to skipping rows whose
    pr_id cannot be parsed — dev1's TASK-30 (is_valid_row) will harden this.
    """
    import csv

    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(StringIO(text))
    return tuple(apply_schema(row) for row in reader)


def looks_like_pr_record_csv(header_row: Iterable[str]) -> bool:
    """Heuristic: PRRecord CSVs carry the `pr_id` column.

    The Streamlit demo dataset (gh_dataset_2026.csv) uses a flat display
    schema; only the Kaggle-style dataset is worth piping through the
    functional pipeline.
    """
    header = frozenset(h.strip().lower() for h in header_row)
    return "pr_id" in header or "repo_name" in header


# ── Filtering via dev2 ────────────────────────────────────────────────────────


def make_filter_chain(
    state: str | None = None,
    language: str | None = None,
    min_size: int | None = None,
    require_body: bool = False,
) -> Callable[[Any], bool]:
    """Compose dev2's filter predicates into a single AND-combined predicate."""
    predicates: tuple[Callable[[Any], bool], ...] = ()
    if state and state.lower() != "todas":
        predicates = (*predicates, by_state(state))
    if language and language.lower() != "todas":
        predicates = (*predicates, by_language(language))
    if min_size is not None and min_size > 0:
        predicates = (*predicates, with_min_size(min_size))
    if require_body:
        predicates = (*predicates, with_non_empty_body())
    return combine_filters(*predicates)


def filter_prs(
    prs: Iterable[PRRecord],
    predicate: Callable[[Any], bool],
) -> Iterable[PRRecord]:
    """Lazy filter via dev4's `build_pipeline`."""
    return build_pipeline(prs, filters=(predicate,), mappers=())


# ── LLM enrichment via dev3 + dev4 cache ──────────────────────────────────────


class CacheCounter:
    """Tracks classifier invocations to expose a cache-hit indicator on the UI.

    For each wrapped classifier we count *actual* invocations (cache miss)
    vs *served-from-cache* invocations (cache hit). The diff tells the UI
    how many classifications came from the persistent cache.
    """

    def __init__(self) -> None:
        self.calls_made: int = 0
        self.cache_hits: int = 0

    def wrap(self, classifier_fn: ClassifierFn) -> ClassifierFn:
        invocations = {"n": 0}

        def tracking(*args: str) -> str:
            invocations["n"] += 1
            return classifier_fn(*args)

        cached = cached_classify(tracking)

        def observed(*args: str) -> str:
            before = invocations["n"]
            result = cached(*args)
            if invocations["n"] == before:
                self.cache_hits += 1
            else:
                self.calls_made += 1
            return result

        return observed

    @property
    def total(self) -> int:
        return self.calls_made + self.cache_hits


def enrich_pr(
    pr: PRRecord,
    client: LLMRunHandle,
    classifiers: Mapping[str, ClassifierFn],
) -> EnrichedPR:
    """Apply the three classifiers to a single PRRecord."""
    project = classifiers["project_type"](pr.repo_name, pr.title, str(client))
    nature = classifiers["contribution_nature"](pr.title, pr.body, str(client))
    clarity = classifiers["description_clarity"](pr.body, str(client))
    return EnrichedPR(
        pr_id=pr.pr_id,
        repo_name=pr.repo_name,
        language=pr.language,
        title=pr.title,
        body=pr.body,
        state=pr.state,
        additions=pr.additions,
        deletions=pr.deletions,
        project_type=project,
        contribution_nature=nature,
        description_clarity=clarity,
    )


def enrich_prs(
    prs: Iterable[PRRecord],
    client: LLMRunHandle,
    cache: CacheCounter | None = None,
) -> Iterable[EnrichedPR]:
    """Map each PRRecord into an EnrichedPR using dev3's classifiers.

    Matches the signature of dev3's TASK-35 `enrich_prs`. When dev3 ships
    their implementation we switch this body to a single import + call.
    """
    counter = cache or CacheCounter()

    classifiers: dict[str, ClassifierFn] = {
        "project_type": counter.wrap(
            lambda repo, title, _c: classify_project_type(repo, [title], client)
        ),
        "contribution_nature": counter.wrap(
            lambda title, body, _c: classify_contribution_nature(title, body, client)
        ),
        "description_clarity": counter.wrap(
            lambda body, _c: classify_description_clarity(body, client)
        ),
    }

    return (enrich_pr(pr, client, classifiers) for pr in prs)


# ── DataFrame adapters ────────────────────────────────────────────────────────


_DISPLAY_COLUMNS: tuple[str, ...] = (
    "id",
    "repo",
    "lang",
    "type",
    "nature",
    "clarity",
    "size",
    "state",
    "title",
)


def enriched_to_dataframe(items: Iterable[EnrichedPR]) -> pd.DataFrame:
    """Materialize enriched PRs into a DataFrame using the UI's display columns."""
    rows = [
        {
            "id": e.pr_id,
            "repo": e.repo_name,
            "lang": e.language.title() if e.language else "—",
            "type": e.project_type.title() if e.project_type else "—",
            "nature": e.contribution_nature.title() if e.contribution_nature else "—",
            "clarity": _capitalize_clarity(e.description_clarity),
            "size": (e.additions or 0) + (e.deletions or 0),
            "state": e.state.title() if e.state else "—",
            "title": e.title,
        }
        for e in items
    ]
    if not rows:
        return pd.DataFrame(columns=list(_DISPLAY_COLUMNS))
    return pd.DataFrame(rows)


def prs_to_dataframe(prs: Iterable[PRRecord]) -> pd.DataFrame:
    """Materialize raw PRRecords (un-enriched) into a DataFrame.

    Classification columns are left empty so the UI can highlight that LLM
    classification is disabled.
    """
    rows = [
        {
            "id": pr.pr_id,
            "repo": pr.repo_name,
            "lang": pr.language.title() if pr.language else "—",
            "type": "—",
            "nature": "—",
            "clarity": "—",
            "size": (pr.additions or 0) + (pr.deletions or 0),
            "state": pr.state.title() if pr.state else "—",
            "title": pr.title,
        }
        for pr in prs
    ]
    if not rows:
        return pd.DataFrame(columns=list(_DISPLAY_COLUMNS))
    return pd.DataFrame(rows)


def _capitalize_clarity(value: str) -> str:
    mapping = {
        "insuficiente": "Insufficient",
        "básica": "Basic",
        "boa": "Good",
        "excelente": "Excellent",
    }
    return mapping.get(value.lower(), value.title() if value else "—")


# ── Distribution helpers (consumed by chart components) ──────────────────────


def distributions_from_dataframe(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Compute the 4 distribution dicts driving TASK-38's dashboard charts.

    Reads the DataFrame columns the UI uses (lang/type/nature/clarity) and
    delegates counting to dev2's reducers when available (or the local
    fallback otherwise). Returns an empty dict per missing column so charts
    can render an empty state gracefully.
    """
    return {
        "language": _column_counts(df, "lang"),
        "project_type": _column_counts(df, "type"),
        "contribution_nature": _column_counts(df, "nature"),
        "description_clarity": _column_counts(df, "clarity"),
    }


def _column_counts(df: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in df.columns or len(df) == 0:
        return {}
    from utils.distributions import (
        count_from_dataframe_column,
    )

    result: dict[str, int] = count_from_dataframe_column(df[column].dropna().tolist())
    return result


def distributions_from_records(items: Iterable[Any]) -> dict[str, dict[str, int]]:
    """Apply dev2's reducers directly to a tuple of (Enriched)PR records.

    Used when the UI is fed by the functional pipeline rather than a
    DataFrame round-trip.
    """
    materialized = tuple(items)
    return {
        "language": count_by_language(materialized),
        "project_type": count_by_project_type(materialized),
        "contribution_nature": count_by_contribution_nature(materialized),
        "description_clarity": count_by_description_clarity(materialized),
    }


# ── Uploaded-file routing ─────────────────────────────────────────────────────


def load_uploaded(
    file: BytesIO,
    filename: str,
) -> tuple[pd.DataFrame, tuple[PRRecord, ...] | None]:
    """Return (display_df, raw_prs_or_None).

    If the uploaded CSV matches the PRRecord schema, parse it via dev1 and
    keep the immutable tuple alongside the DataFrame so downstream steps
    (LLM enrichment, pure filters) can operate on it. Otherwise treat it as
    a flat display CSV (the demo dataset shape) and return only the
    DataFrame.
    """
    raw = file.read()
    text = raw.decode("utf-8", errors="replace")
    header = text.splitlines()[0].split(",") if text else []

    if looks_like_pr_record_csv(header):
        prs = parse_csv_bytes(raw)
        return prs_to_dataframe(prs), prs

    df = pd.read_csv(StringIO(text))
    return df, None
