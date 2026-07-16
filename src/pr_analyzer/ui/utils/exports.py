"""
exports.py — UI-side wrapper around the project exporters.

This module wraps `pandas.DataFrame.to_csv` / `to_json` so the export tab works
end-to-end while keeping browser serialization isolated from the pure modules.

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
