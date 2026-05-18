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

import pandas as pd


def export_dataframe_csv(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to CSV bytes."""
    csv: str = df.to_csv(index=False) or ""
    return csv.encode("utf-8")


def export_dataframe_json(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to JSON bytes."""
    json: str = df.to_json(orient="records", indent=2) or ""
    return json.encode("utf-8")
