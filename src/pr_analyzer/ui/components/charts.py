"""
components/charts.py — Plotly chart builders for the dashboard tab.
Each function returns a Plotly figure; rendering is left to the caller.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.constants import (
    CLARITY_COLOR,
    CLARITY_ORDER,
    NATURE_COLOR,
    PLOT_BASE,
)

_NO_DATA_MSG = "Sem dados para exibir."
_CHART_CFG   = {"displayModeBar": False}


def render_bar_chart(df: pd.DataFrame) -> None:
    """Stacked bar: PR count by nature/category."""
    st.markdown(
        """
        <div class="chart-panel">
          <div class="chart-panel-accent"></div>
          <div class="chart-panel-title">📊 Classificação Semântica de Contribuições</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "nature" not in df.columns or len(df) == 0:
        st.info(_NO_DATA_MSG)
        return

    nc = df["nature"].value_counts().reset_index()
    nc.columns = ["Natureza", "Qtd"]

    fig = go.Figure(
        go.Bar(
            x=nc["Natureza"],
            y=nc["Qtd"],
            marker_color=[NATURE_COLOR.get(n, "#818cf8") for n in nc["Natureza"]],
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>%{y} PRs<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOT_BASE,
        showlegend=False,
        bargap=0.35,
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#52525b")),
        yaxis=dict(
            showgrid=True, gridcolor="#27272a", zeroline=False,
            tickfont=dict(size=10, color="#52525b"), gridwidth=0.5,
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def render_scatter_chart(df: pd.DataFrame) -> None:
    """Scatter: commit size vs clarity level."""
    st.markdown(
        """
        <div class="chart-panel">
          <div class="chart-panel-title">📄 Correlação: Qualidade vs Escopo</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not {"size", "clarity", "repo"}.issubset(df.columns) or len(df) == 0:
        st.info(_NO_DATA_MSG)
        return

    fig = px.scatter(
        df,
        x="size",
        y="clarity",
        color="clarity",
        hover_data=["repo", "lang"],
        color_discrete_map=CLARITY_COLOR,
        category_orders={"clarity": CLARITY_ORDER},
        labels={"size": "", "clarity": ""},
    )
    fig.update_layout(
        **PLOT_BASE,
        showlegend=False,
        xaxis=dict(
            showgrid=False, zeroline=False,
            ticksuffix=" chars", tickfont=dict(size=9, color="#52525b"),
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#27272a", gridwidth=0.5,
            zeroline=False, tickfont=dict(size=9, color="#52525b"),
        ),
    )
    fig.update_traces(marker=dict(size=13, opacity=0.8, line=dict(width=0)))
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def render_lang_donut(df: pd.DataFrame) -> None:
    """Donut chart: distribution by programming language."""
    st.markdown(
        """
        <div class="chart-panel">
          <div class="chart-panel-accent" style="background:linear-gradient(180deg,#34d399,#059669);"></div>
          <div class="chart-panel-title">🌐 Distribuição por Linguagem</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "lang" not in df.columns or len(df) == 0:
        st.info(_NO_DATA_MSG)
        return

    lc = df["lang"].value_counts().reset_index()
    lc.columns = ["Linguagem", "Qtd"]

    fig = go.Figure(
        go.Pie(
            labels=lc["Linguagem"],
            values=lc["Qtd"],
            hole=0.62,
            marker=dict(
                colors=["#818cf8", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#60a5fa"],
                line=dict(color="#09090b", width=2),
            ),
            hovertemplate="<b>%{label}</b><br>%{value} PRs (%{percent})<extra></extra>",
            textinfo="none",
        )
    )
    fig.update_layout(**PLOT_BASE)
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def render_clarity_gauge(df: pd.DataFrame) -> None:
    """Gauge: average clarity score (0–100)."""
    st.markdown(
        """
        <div class="chart-panel">
          <div class="chart-panel-accent" style="background:linear-gradient(180deg,#fbbf24,#f59e0b);"></div>
          <div class="chart-panel-title">🎯 Score Médio de Clareza</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "clarity" not in df.columns or len(df) == 0:
        st.info(_NO_DATA_MSG)
        return

    order  = {"Excellent": 100, "Good": 75, "Basic": 40, "Insufficient": 10}
    avg    = df["clarity"].map(order).mean()
    score  = round(avg) if not pd.isna(avg) else 0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 32, "color": "#f4f4f5", "family": "Inter"}},
            gauge={
                "axis":  {"range": [0, 100], "tickcolor": "#52525b", "tickfont": {"size": 9}},
                "bar":   {"color": "#6366f1", "thickness": 0.25},
                "bgcolor": "#27272a",
                "steps": [
                    {"range": [0, 40],   "color": "rgba(248,113,113,.15)"},
                    {"range": [40, 75],  "color": "rgba(251,191,36,.10)"},
                    {"range": [75, 100], "color": "rgba(52,211,153,.10)"},
                ],
                "threshold": {
                    "line": {"color": "#818cf8", "width": 2},
                    "thickness": 0.75,
                    "value": 80,
                },
            },
        )
    )
    fig.update_layout(**{**PLOT_BASE, "height": 220})
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)