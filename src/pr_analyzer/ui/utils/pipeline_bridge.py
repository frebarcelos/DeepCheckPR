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

import os
from collections.abc import Callable, Iterable, Mapping
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

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

from pr_analyzer.io import PRRecord, apply_schema, detect_schema, schema_adapter
from pr_analyzer.llm.classifiers import enrich_prs as backend_enrich_prs
from pr_analyzer.llm.client import LLMClient, create_llm_client
from pr_analyzer.llm.metrics import ClassificationMetrics
from pr_analyzer.llm.system_probe import (
    format_report,
    get_model_size_gb,
    load_pipeline_config,
    probe_system,
    recommend_config,
)
from pr_analyzer.pipeline.builder import build_pipeline
from pr_analyzer.transforms import (
    by_language,
    by_state,
    combine_filters,
    with_min_size,
    with_non_empty_body,
)
from pr_analyzer.transforms.reducers import EnrichedPR

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


# ── Type aliases ──────────────────────────────────────────────────────────────

ClassifierFn = Callable[..., str]


# ── CSV ingestion via dev1 ────────────────────────────────────────────────────


def parse_csv_bytes(raw: bytes) -> tuple[PRRecord, ...]:
    """Convert raw CSV bytes (uploaded file) into an immutable tuple of PRRecords.

    Detects the CSV schema (canonical or github_export) and adapts column names
    before calling apply_schema, so fields like `description`→`body` are mapped.
    """
    import csv

    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(StringIO(text))
    schema = detect_schema(reader.fieldnames or [])
    adapt = schema_adapter(schema) if schema != "unknown" else lambda r: dict(r)
    return tuple(apply_schema(adapt(row)) for row in reader)


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


def enrich_prs(
    prs: Iterable[PRRecord],
    client: LLMClient | None = None,
    cache_path: Path = Path(".cache/ui_llm.db"),
    metrics: ClassificationMetrics | None = None,
) -> Iterable[EnrichedPR]:
    """Delegate enrichment to the real backend implementation.

    LLM_MAX_WORKERS=4   → processa 4 PRs em paralelo (ThreadPoolExecutor)
    LLM_USE_TOOLS=true  → 1 chamada por PR via tool calling (requer qwen2:1.5b+)
    cache_path           → SQLite result-cache; resultados anteriores não são reclassificados.
    metrics              → acumula cache_hits e throughput; None = sem coleta.
    """
    llm_client = client or create_llm_client()
    cfg = load_pipeline_config()
    return backend_enrich_prs(
        prs=prs,
        client=llm_client,
        cache_path=cache_path,
        max_workers=int(cfg["max_workers"]),
        use_tools=bool(cfg["use_tools"]),
        batch_size=int(cfg["batch_size"]),
        metrics=metrics,
    )


def get_system_report() -> str:
    """Retorna relatório legível do hardware e configuração recomendada para a UI."""
    profile = probe_system()
    model = os.environ.get("LLM_MODEL", "llama3")
    model_size = get_model_size_gb(model)
    config = recommend_config(profile, model_size)
    return format_report(profile, config)


# ── DataFrame adapters ────────────────────────────────────────────────────────


_DISPLAY_COLUMNS: tuple[str, ...] = (
    "id",
    "repo",
    "lang",
    "type",
    "nature",
    "clarity",
    "complexity",
    "size",
    "chars",
    "words",
    "state",
    "title",
)


def enriched_to_dataframe(items: Iterable[Any]) -> pd.DataFrame:
    """Materialize enriched PRs into a DataFrame using the UI's display columns."""
    rows = [
        {
            "id": e.pr.pr_id,
            "repo": e.pr.repo_name,
            "lang": e.pr.language.title() if e.pr.language else "—",
            "type": e.project_type.title() if e.project_type else "—",
            "nature": e.contribution_nature.title() if e.contribution_nature else "—",
            "clarity": _capitalize_clarity(e.description_clarity),
            "complexity": e.review_complexity.title() if e.review_complexity else "—",
            "size": (e.pr.additions or 0) + (e.pr.deletions or 0),
            "chars": len(e.pr.body) if e.pr.body else 0,
            "words": len(e.pr.body.split()) if e.pr.body else 0,
            "state": e.pr.state.title() if e.pr.state else "—",
            "title": e.pr.title,
        }
        for e in items
    ]
    if not rows:
        return pd.DataFrame(columns=list(_DISPLAY_COLUMNS))
    return pd.DataFrame(rows)


def prs_to_dataframe(prs: Iterable[PRRecord]) -> pd.DataFrame:
    """Materialize raw PRRecords (un-enriched) into a DataFrame."""
    rows = [
        {
            "id": pr.pr_id,
            "repo": pr.repo_name,
            "lang": pr.language.title() if pr.language else "—",
            "type": "—",
            "nature": "—",
            "clarity": "—",
            "size": (pr.additions or 0) + (pr.deletions or 0),
            "chars": len(pr.body) if pr.body else 0,
            "words": len(pr.body.split()) if pr.body else 0,
            "state": pr.state.title() if pr.state else "—",
            "title": pr.title,
        }
        for pr in prs
    ]
    if not rows:
        return pd.DataFrame(columns=list(_DISPLAY_COLUMNS))
    return pd.DataFrame(rows)


def dataframe_to_prs(df: pd.DataFrame) -> tuple[PRRecord, ...]:
    """Best-effort conversion from a displayed DataFrame back to PRRecords.

    Supports three schemas:
    - canonical:      pr_id, repo_name, language, title, state
    - mined_comments: id, repo, lang, comment
    - flat_ui:        id, repo, lang  (mock/display format, body synthesized)

    Returns an empty tuple only when none of the three schemas match.
    """
    if df is None or len(df) == 0:
        return ()

    columns = {str(c) for c in df.columns}
    canonical = {"pr_id", "repo_name", "language", "title", "state"}
    mined_comments = {"id", "repo", "lang", "comment"}
    flat_ui = {"id", "repo", "lang"}

    if not (
        canonical.issubset(columns)
        or mined_comments.issubset(columns)
        or flat_ui.issubset(columns)
    ):
        return ()

    def _first(row: Mapping[str, Any], *names: str, default: Any = "") -> Any:
        for name in names:
            value = row.get(name, None)
            if value not in (None, ""):
                return value
        return default

    records: list[PRRecord] = []
    for _, raw_row in df.iterrows():
        row = raw_row.to_dict()
        # synthesize a title from nature/type when no explicit title or comment
        synthetic_title = _first(row, "title", "comment", "nature", "type", default="")
        body = _first(row, "body", "comment", default="")
        records.append(
            apply_schema(
                {
                    "pr_id": _first(row, "pr_id", "id", default=""),
                    "repo_name": _first(row, "repo_name", "repo", default=""),
                    "language": _first(row, "language", "lang", default=""),
                    "title": synthetic_title,
                    "body": body,
                    "state": _first(row, "state", default="open"),
                    "created_at": _first(row, "created_at", "date", default=""),
                    "merged_at": _first(row, "merged_at", default=""),
                    "additions": _first(row, "additions", "size", default=""),
                    "deletions": _first(row, "deletions", default=0),
                    "changed_files": _first(row, "changed_files", default=1),
                }
            )
        )

    return tuple(records)


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
    DataFrame when it cannot be mapped back to PRRecord.
    """
    raw = file.read()
    text = raw.decode("utf-8", errors="replace")
    header = text.splitlines()[0].split(",") if text else []

    if looks_like_pr_record_csv(header):
        prs = parse_csv_bytes(raw)
        return prs_to_dataframe(prs), prs

    df = pd.read_csv(StringIO(text))
    prs = dataframe_to_prs(df)
    return df, prs or None
