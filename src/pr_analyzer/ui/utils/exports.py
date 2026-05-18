"""
exports.py — UI-side wrapper around dev1's exporters (TASK-48 prep).

Today this module wraps `pandas.DataFrame.to_csv` / `to_json` so the export
tab works end-to-end. When dev1 ships `pr_analyzer.io.exporters` with
`export_to_csv` / `export_to_json` (their TASK-13/14 deliverable referenced
by fase-4 TASK-48), this file becomes a one-line passthrough.

Side-effect module — exporters serialize bytes for `st.download_button` to
hand over to the user's browser.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pandas as pd

# ── Dev1 exporters (when available) ──────────────────────────────────────────
# Soft import: dev1's `io.exporters` will provide `export_to_csv(records)` and
# `export_to_json(records)`. Until then we fall back to pandas serialization.


def _load_dev1_exporters() -> (
    tuple[Callable[[Any], bytes] | None, Callable[[Any], bytes] | None]
):
    try:
        from pr_analyzer.io.exporters import export_to_csv, export_to_json
    except ImportError:
        return None, None
    return export_to_csv, export_to_json


_DEV1_CSV, _DEV1_JSON = _load_dev1_exporters()


def export_dataframe_csv(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to CSV bytes. Prefers dev1's exporter when present."""
    if _DEV1_CSV is not None and "id" in df.columns:
        # When dev1 lands, hand off the records directly so their pure
        # serializer owns the format (line endings, quoting, encoding).
        try:
            return cast(bytes, _DEV1_CSV(df.to_dict(orient="records")))
        except Exception:
            pass
    return df.to_csv(index=False).encode("utf-8")


def export_dataframe_json(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to JSON bytes. Prefers dev1's exporter when present."""
    if _DEV1_JSON is not None and "id" in df.columns:
        try:
            return cast(bytes, _DEV1_JSON(df.to_dict(orient="records")))
        except Exception:
            pass
    return df.to_json(orient="records", indent=2).encode("utf-8")
