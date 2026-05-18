"""
components/kpis.py — KPI row rendered at the top of the dashboard tab.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_kpis(df: pd.DataFrame, metrics_active: bool) -> None:
    """Render four KPI metric cards in a horizontal row."""
    k1, k2, k3, k4 = st.columns(4, gap="small")

    k1.metric("● PRs Processados", len(df))
    k2.metric("● Clareza (LLM)", _compute_clarity_grade(df))
    k3.metric("● Volatilidade", _compute_volatility(df))
    k4.metric("● Cache Agno", "Ativo" if metrics_active else "Inativo")


# ── Pure helpers ──────────────────────────────────────────────────────────────


def _compute_clarity_grade(df: pd.DataFrame) -> str:
    if "clarity" not in df.columns or len(df) == 0:
        return "—"
    order = {"Excellent": 4, "Good": 3, "Basic": 2, "Insufficient": 1}
    avg = df["clarity"].map(order).mean()
    if avg >= 3.5:
        return "Nível A"
    if avg >= 2.5:
        return "Nível B+"
    if avg >= 1.5:
        return "Nível C"
    return "Nível D"


def _compute_volatility(df: pd.DataFrame) -> str:
    if "size" not in df.columns or len(df) == 0:
        return "—"
    mean = df["size"].mean()
    std = df["size"].std()
    # std is NaN for a single row; mean can be NaN if all values are null
    if pd.isna(mean) or pd.isna(std) or mean == 0:
        return "—"
    cv = std / mean
    if cv < 0.4:
        return "Baixa"
    if cv < 0.8:
        return "Média"
    return "Alta"