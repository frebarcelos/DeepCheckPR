"""
data.py — Pure data helpers (no Streamlit, no global state).
All functions are referentially transparent given the same inputs.
"""

from __future__ import annotations

import json
import os
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

MAX_DATASET_SIZE_GB: float = float(os.environ.get("MAX_DATASET_SIZE_GB", "10"))


@st.cache_data(show_spinner=False)
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


def _is_mined_comments(data: Any) -> bool:
    """Return True when data matches the mined-comments archive shape.

    Expected shape: { "owner/repo": [ {comment_dict}, ... ], ... }
    """
    if not isinstance(data, dict):
        return False
    sample = next(iter(data.values()), None)
    return isinstance(sample, list)


def _mined_comments_to_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    """Flatten a mined-comments dict into a UI-compatible DataFrame.

    Re-uses the same _comment_row / heuristics that load_archive_sample uses,
    so the display columns are identical whether the file came from upload or
    from the local dataset picker.
    """
    rows: list[dict[str, Any]] = []
    for repo_full, comments in data.items():
        if not isinstance(comments, list):
            continue
        for c in comments:
            file_path = str(c.get("path", ""))
            body = str(c.get("body", ""))
            lang_fallback = repo_full.split("/")[-1] if "/" in repo_full else repo_full
            rows.append(
                _comment_row(
                    int(c.get("id", len(rows))),
                    repo_full,
                    file_path,
                    body,
                    lang_fallback,
                )
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def load_dataframe(file: BytesIO, filename: str) -> pd.DataFrame:
    """Parse an uploaded file into a DataFrame.

    Handles three JSON shapes:
      - mined-comments archive: { "owner/repo": [{comment}, ...] }
      - list of records:        [ {row}, ... ]
      - flat dict:              { col: [values] }

    Raises ValueError with a descriptive message on failure.
    """
    try:
        if filename.endswith(".json"):
            data = json.load(file)
            if _is_mined_comments(data):
                return _mined_comments_to_dataframe(data)
            return pd.DataFrame(data)
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


# ─── Local dataset discovery ─────────────────────────────────────────────────

_EXT_TO_LANG: dict[str, str] = {
    ".java": "Java",
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".go": "Go",
    ".rb": "Ruby",
    ".rs": "Rust",
}


def discover_datasets(
    data_dir: str,
    max_size_gb: float = MAX_DATASET_SIZE_GB,
) -> list[dict[str, Any]]:
    """Return available datasets in data_dir (top-level files + archive subdirs).

    Files larger than max_size_gb are listed but flagged as oversized so the UI
    can warn the user instead of silently skipping them.
    """
    base = Path(data_dir)
    if not base.is_dir():
        return []

    results: list[dict[str, Any]] = []
    max_bytes = max_size_gb * 1024**3

    for entry in sorted(base.iterdir()):
        if entry.is_file() and entry.suffix in (".csv", ".json"):
            size_bytes = entry.stat().st_size
            mb = size_bytes / 1024**2
            oversized = size_bytes > max_bytes
            label = f"{entry.name}  ({mb:.1f} MB)"
            if oversized:
                label += f"  ⚠ >{max_size_gb:.0f} GB"
            results.append(
                {
                    "label": label,
                    "path": str(entry),
                    "format": entry.suffix.lstrip("."),
                    "lang": None,
                    "oversized": oversized,
                }
            )

    archive = base / "archive"
    if archive.is_dir():
        for sub in sorted(archive.iterdir()):
            inner = sub / sub.name
            if sub.is_dir() and inner.is_file():
                size_bytes = inner.stat().st_size
                gb = size_bytes / 1024**3
                oversized = size_bytes > max_bytes
                lang = sub.name.replace("mined-comments-25stars-25prs-", "").replace(
                    ".json", ""
                )
                label = f"{lang}  ({gb:.1f} GB · amostra)"
                if oversized:
                    label += f"  ⚠ >{max_size_gb:.0f} GB"
                results.append(
                    {
                        "label": label,
                        "path": str(inner),
                        "format": "archive",
                        "lang": lang,
                        "oversized": oversized,
                    }
                )

    return results


def check_ollama(host: str) -> tuple[bool, list[str]]:
    """Return (is_running, model_names) for the Ollama instance at host."""
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=2) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
            return True, [str(m["name"]) for m in data.get("models", [])]
    except Exception:
        return False, []


@st.cache_data(show_spinner=False)
def load_archive_sample(
    path: str,
    lang: str,
    max_records: int = 2000,
) -> pd.DataFrame:
    """Stream first max_records review comments from a mined-comments JSON archive."""
    try:
        import ijson
    except ImportError as exc:
        raise RuntimeError("Instale ijson: pip install ijson") from exc

    rows: list[dict[str, Any]] = []
    with open(path, "rb") as f:
        for repo, comments in ijson.kvitems(f, ""):
            for c in comments:
                body = str(c.get("body", ""))
                rows.append(
                    _comment_row(
                        int(c.get("id", len(rows))),
                        str(repo),
                        str(c.get("path", "")),
                        body,
                        lang,
                    )
                )
                if len(rows) >= max_records:
                    return pd.DataFrame(rows)
    return pd.DataFrame(rows)


def _comment_row(
    cid: int,
    repo: str,
    file_path: str,
    body: str,
    fallback: str,
) -> dict[str, Any]:
    """Convert a mined-comment dict to a UI-compatible row."""
    ext = os.path.splitext(file_path)[1].lower()
    return {
        "id": cid,
        "repo": repo.split("/")[-1],
        "lang": _EXT_TO_LANG.get(ext, fallback),
        "type": "Code Review",
        "nature": _nature_heuristic(body),
        "clarity": _clarity_heuristic(body),
        "size": len(body),
        "date": "",
        "comment": body[:200],
    }


def _nature_heuristic(body: str) -> str:
    """Classify comment nature by keyword heuristic."""
    lower = body.lower()
    if any(w in lower for w in ("bug", "fix", "error", "crash", "issue")):
        return "Bug Fix"
    if any(w in lower for w in ("add", "new", "implement", "feature", "support")):
        return "Feature"
    if any(w in lower for w in ("refactor", "clean", "simplif", "extract")):
        return "Refactor"
    return "Documentation"


def _clarity_heuristic(body: str) -> str:
    """Estimate comment clarity from body length."""
    n = len(body)
    if n >= 100:
        return "Excellent"
    if n >= 50:
        return "Good"
    if n >= 20:
        return "Basic"
    return "Insufficient"


# ─── Filtering (pure transform) ──────────────────────────────────────────────


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