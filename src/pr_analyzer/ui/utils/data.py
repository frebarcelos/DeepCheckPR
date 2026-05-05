"""
data.py — Pure data helpers (no Streamlit, no global state).
All functions are referentially transparent given the same inputs.
"""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

# ─── Mock / demo dataset ─────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)  # type: ignore[misc]
def get_mock_data() -> pd.DataFrame:
    """Return a small but representative demo DataFrame."""
    rows: list[dict[str, Any]] = [
        {
            "id": 1,
            "lang": "Python",
            "type": "Library",
            "nature": "Bug Fix",
            "clarity": "Excellent",
            "size": 450,
            "repo": "pandas",
            "date": "2024-03-01",
        },
        {
            "id": 2,
            "lang": "JavaScript",
            "type": "Framework",
            "nature": "Feature",
            "clarity": "Basic",
            "size": 120,
            "repo": "next.js",
            "date": "2024-03-02",
        },
        {
            "id": 3,
            "lang": "Go",
            "type": "CLI Tool",
            "nature": "Refactor",
            "clarity": "Good",
            "size": 300,
            "repo": "terraform",
            "date": "2024-03-02",
        },
        {
            "id": 4,
            "lang": "Python",
            "type": "Library",
            "nature": "Feature",
            "clarity": "Good",
            "size": 800,
            "repo": "scikit-learn",
            "date": "2024-03-03",
        },
        {
            "id": 5,
            "lang": "TypeScript",
            "type": "Web App",
            "nature": "Documentation",
            "clarity": "Insufficient",
            "size": 50,
            "repo": "vscode",
            "date": "2024-03-04",
        },
        {
            "id": 6,
            "lang": "Java",
            "type": "Framework",
            "nature": "Bug Fix",
            "clarity": "Excellent",
            "size": 600,
            "repo": "spring",
            "date": "2024-03-05",
        },
    ]
    return pd.DataFrame(rows)


# ─── Loading from uploaded files ─────────────────────────────────────────────


def load_dataframe(file: BytesIO, filename: str) -> pd.DataFrame:
    """
    Parse an uploaded file into a DataFrame.
    Raises ValueError with a descriptive message on failure.
    """
    try:
        if filename.endswith(".json"):
            return pd.DataFrame(json.load(file))
        return pd.read_csv(file)
    except Exception as exc:
        raise ValueError(f"Não foi possível ler '{filename}': {exc}") from exc


# ─── Filtering (pure transform) ──────────────────────────────────────────────


def apply_filters(
    df: pd.DataFrame,
    lang: str,
    nature: str,
) -> pd.DataFrame:
    """Return a filtered copy of *df* without mutating the original."""
    result = df.copy()
    if lang != "Todas" and "lang" in result.columns:
        result = result[result["lang"] == lang]
    if nature != "Todas" and "nature" in result.columns:
        result = result[result["nature"] == nature]
    return result


# ─── Export helpers ───────────────────────────────────────────────────────────


def build_report_markdown(df: pd.DataFrame) -> str:
    """Generate a plain-text executive report from *df*."""
    top_lang = df["lang"].mode()[0] if len(df) and "lang" in df.columns else "—"
    nat_lines = ""
    if "nature" in df.columns and len(df):
        nat_lines = "\n".join(
            f"- {n}: {c}" for n, c in df["nature"].value_counts().items()
        )
    return (
        f"# GitAnalyzer — Relatório Executivo\n\n"
        f"**PRs Processados:** {len(df)}\n"
        f"**Linguagem Top:** {top_lang}\n\n"
        f"## Distribuição por Natureza\n{nat_lines}"
    )


def get_filter_options(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return (lang_options, nature_options) including a 'Todas' sentinel."""
    langs = (
        ["Todas", *sorted(df["lang"].dropna().unique().tolist())]
        if "lang" in df.columns
        else ["Todas"]
    )
    natures = (
        ["Todas", *sorted(df["nature"].dropna().unique().tolist())]
        if "nature" in df.columns
        else ["Todas"]
    )
    return langs, natures
