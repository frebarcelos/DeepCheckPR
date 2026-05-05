"""
constants.py — Design tokens, colour maps, and chart defaults.
Pure values; no imports from Streamlit or pandas.
"""

from typing import Any

# ── Colour maps ───────────────────────────────────────────────────────────────
NATURE_COLOR: dict[str, str] = {
    "Bug Fix": "#818cf8",
    "Feature": "#34d399",
    "Refactor": "#fbbf24",
    "Documentation": "#a78bfa",
}

CLARITY_COLOR: dict[str, str] = {
    "Excellent": "#34d399",
    "Good": "#818cf8",
    "Basic": "#fbbf24",
    "Insufficient": "#f87171",
}

CLARITY_ORDER: list[str] = ["Excellent", "Good", "Basic", "Insufficient"]

# ── Plotly base layout (shared across all charts) ────────────────────────────
PLOT_BASE: dict[str, Any] = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, sans-serif", "color": "#52525b", "size": 10},
    "margin": {"l": 4, "r": 4, "t": 8, "b": 4},
    "height": 280,
}

# ── KPI metadata ─────────────────────────────────────────────────────────────
KPI_COLORS: list[str] = ["#818cf8", "#34d399", "#fbbf24", "#a1a1aa"]

# ── Column display preferences ───────────────────────────────────────────────
PREFERRED_COLS: list[str] = [
    "date",
    "repo",
    "lang",
    "type",
    "nature",
    "clarity",
    "size",
]

COL_RENAMES: dict[str, str] = {
    "date": "Data",
    "repo": "Repositório",
    "lang": "Linguagem",
    "type": "Tipo",
    "nature": "Natureza (ML)",
    "clarity": "Status LLM",
    "size": "Tamanho",
}

# ── App metadata ─────────────────────────────────────────────────────────────
APP_VERSION = "2.0"
APP_NAME = "GitAnalyzer"
