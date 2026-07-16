"""
components/charts.py — Plotly chart builders for the dashboard tab.

Distribution charts consume `dict[str, int]` directly, matching the API of
the `count_by_*` reducers. This keeps the UI
layer decoupled from pandas and lets the same chart functions be reused
when fed either a DataFrame round-trip or the raw functional pipeline.

Each function returns nothing — Streamlit-side rendering happens inline so
this module stays the only place that touches plotly + st.plotly_chart.
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


def _chart_cfg() -> dict[str, bool]:
    return {"displayModeBar": False}


def _gauge_opts() -> dict[str, object]:
    return {
        "number": {
            "suffix": "%",
            "font": {"size": 32, "color": "#f4f4f5", "family": "Inter"},
        },
        "gauge": {
            "axis": {
                "range": [0, 100],
                "tickcolor": "#52525b",
                "tickfont": {"size": 9},
            },
            "bar": {"color": "#6366f1", "thickness": 0.25},
            "bgcolor": "#27272a",
            "steps": [
                {"range": [0, 40], "color": "rgba(248,113,113,.15)"},
                {"range": [40, 75], "color": "rgba(251,191,36,.10)"},
                {"range": [75, 100], "color": "rgba(52,211,153,.10)"},
            ],
            "threshold": {
                "line": {"color": "#818cf8", "width": 2},
                "thickness": 0.75,
                "value": 80,
            },
        },
    }


_DEFAULT_PALETTE: tuple[str, ...] = (
    "#818cf8",
    "#34d399",
    "#fbbf24",
    "#f87171",
    "#a78bfa",
    "#60a5fa",
    "#fb7185",
    "#22d3ee",
)


# ── Distribution charts ──────────────────────────────────────────────────────


def render_distribution_bar(
    counts: dict[str, int],
    title: str,
    accent_gradient: str = "linear-gradient(180deg,#818cf8,#4f46e5)",
    color_map: dict[str, str] | None = None,
) -> None:
    """Generic vertical bar chart driven by `dict[str, int]`."""
    _panel_header(title, accent_gradient)

    if not counts:
        st.info(_NO_DATA_MSG)
        return

    labels = list(counts.keys())
    values = list(counts.values())
    colors = _resolve_colors(labels, color_map)

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>%{y} PRs<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOT_BASE,
        showlegend=False,
        bargap=0.35,
        xaxis=_axis_style(grid=False),
        yaxis=_axis_style(grid=True),
    )
    st.plotly_chart(fig, use_container_width=True, config=_chart_cfg())


def render_distribution_donut(
    counts: dict[str, int],
    title: str,
    accent_gradient: str = "linear-gradient(180deg,#34d399,#059669)",
    color_map: dict[str, str] | None = None,
) -> None:
    """Generic donut chart driven by `dict[str, int]`."""
    _panel_header(title, accent_gradient)

    if not counts:
        st.info(_NO_DATA_MSG)
        return

    labels = list(counts.keys())
    values = list(counts.values())
    colors = _resolve_colors(labels, color_map)

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker={"colors": colors, "line": {"color": "#09090b", "width": 2}},
            hovertemplate="<b>%{label}</b><br>%{value} PRs (%{percent})<extra></extra>",
            textinfo="none",
        )
    )
    fig.update_layout(**PLOT_BASE)
    st.plotly_chart(fig, use_container_width=True, config=_chart_cfg())


# ── Pre-bound wrappers for the count_by_* reducers ──────────────────────────


def render_lang_distribution(counts: dict[str, int]) -> None:
    """Distribution by programming language."""
    render_distribution_donut(counts, "🌐 Distribuição por Linguagem")


def render_project_type_distribution(counts: dict[str, int]) -> None:
    """Distribution by classified project type (library / web app / ...)."""
    render_distribution_donut(
        counts,
        "🏗 Distribuição por Tipo de Projeto",
        accent_gradient="linear-gradient(180deg,#a78bfa,#7c3aed)",
    )


def render_nature_distribution(counts: dict[str, int]) -> None:
    """Distribution by contribution nature (bug fix / feature / ...)."""
    render_distribution_bar(
        counts,
        "📊 Distribuição por Natureza da Contribuição",
        color_map=NATURE_COLOR,
    )


def render_clarity_distribution(counts: dict[str, int]) -> None:
    """Distribution by description clarity level."""
    render_distribution_bar(
        counts,
        "🎯 Distribuição por Clareza da Descrição",
        accent_gradient="linear-gradient(180deg,#fbbf24,#f59e0b)",
        color_map=CLARITY_COLOR,
    )


# ── Auxiliary charts (scatter + gauge) ──────────────────────────────────────


def render_scatter_chart(df: pd.DataFrame) -> None:
    """Scatter: commit size vs clarity level."""
    _panel_header("📄 Correlação: Qualidade vs Escopo")

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
        xaxis=_axis_style(grid=False, suffix=" chars"),
        yaxis=_axis_style(grid=True),
    )
    fig.update_traces(marker={"size": 13, "opacity": 0.8, "line": {"width": 0}})
    st.plotly_chart(fig, use_container_width=True, config=_chart_cfg())


def render_clarity_gauge(df: pd.DataFrame) -> None:
    """Gauge: average clarity score (0-100)."""
    _panel_header(
        "🎯 Score Médio de Clareza", "linear-gradient(180deg,#fbbf24,#f59e0b)"
    )

    if "clarity" not in df.columns or len(df) == 0:
        st.info(_NO_DATA_MSG)
        return

    order = {"Excellent": 100, "Good": 75, "Basic": 40, "Insufficient": 10}
    avg = df["clarity"].map(order).mean()
    score = round(avg) if not pd.isna(avg) else 0

    fig = go.Figure(go.Indicator(mode="gauge+number", value=score, **_gauge_opts()))
    fig.update_layout(**{**PLOT_BASE, "height": 220})
    st.plotly_chart(fig, use_container_width=True, config=_chart_cfg())


def render_body_size_chart(df: pd.DataFrame) -> None:
    """Bar chart: avg description length (chars and words) grouped by a dimension.

    US06 — visualizar distribuição de tamanho de descrição estratificada.
    """
    _panel_header(
        "📝 Tamanho de Descrição por Dimensão",
        "linear-gradient(180deg,#34d399,#059669)",
    )

    if "chars" not in df.columns or len(df) == 0:
        st.info(_NO_DATA_MSG)
        return

    dim: str = st.selectbox(
        "Agrupar por",
        ["lang", "type", "nature"],
        format_func=lambda x: {
            "lang": "Linguagem",
            "type": "Tipo",
            "nature": "Natureza",
        }[x],
        key="body_size_dim",
        label_visibility="collapsed",
    )

    if dim not in df.columns:
        st.info(_NO_DATA_MSG)
        return

    agg = (
        df[df[dim] != "—"]
        .groupby(dim)[["chars", "words"]]
        .mean()
        .round(0)
        .reset_index()
        .sort_values("chars", ascending=False)
    )

    if agg.empty:
        st.info(_NO_DATA_MSG)
        return

    fig = px.bar(
        agg,
        x=dim,
        y=["chars", "words"],
        barmode="group",
        color_discrete_map={"chars": "#6366f1", "words": "#34d399"},
        labels={dim: "", "value": "Média", "variable": "Métrica"},
    )
    fig.update_layout(
        **PLOT_BASE,
        legend={"orientation": "h", "y": 1.1, "x": 0},
        yaxis=_axis_style(grid=True),
        xaxis=_axis_style(grid=False),
    )
    st.plotly_chart(fig, use_container_width=True, config=_chart_cfg())


def render_clarity_cross_chart(df: pd.DataFrame) -> None:
    """Grouped bar: clarity distribution crossed with project type or nature.

    US07 — visualizar relação entre clareza, tipo, natureza e linguagem.
    """
    _panel_header("🔗 Clareza por Dimensão", "linear-gradient(180deg,#f472b6,#db2777)")

    required = {"clarity", "type", "nature", "lang"}
    if not required.issubset(df.columns) or len(df) == 0:
        st.info(_NO_DATA_MSG)
        return

    dim: str = st.selectbox(
        "Cruzar clareza com",
        ["type", "nature", "lang"],
        format_func=lambda x: {
            "type": "Tipo de Projeto",
            "nature": "Natureza",
            "lang": "Linguagem",
        }[x],
        key="clarity_cross_dim",
        label_visibility="collapsed",
    )

    filtered = df[(df["clarity"] != "—") & (df[dim] != "—")]
    if filtered.empty:
        st.info(_NO_DATA_MSG)
        return

    counts = filtered.groupby([dim, "clarity"]).size().reset_index(name="count")

    fig = px.bar(
        counts,
        x=dim,
        y="count",
        color="clarity",
        barmode="group",
        color_discrete_map=CLARITY_COLOR,
        category_orders={"clarity": CLARITY_ORDER},
        labels={dim: "", "count": "PRs", "clarity": "Clareza"},
    )
    fig.update_layout(
        **PLOT_BASE,
        legend={"orientation": "h", "y": 1.1, "x": 0},
        yaxis=_axis_style(grid=True),
        xaxis=_axis_style(grid=False),
    )
    st.plotly_chart(fig, use_container_width=True, config=_chart_cfg())


# ── Private helpers ──────────────────────────────────────────────────────────


def _panel_header(
    title: str,
    accent_gradient: str = "linear-gradient(180deg,#818cf8,#4f46e5)",
) -> None:
    st.markdown(
        f"""
        <div class="chart-panel">
          <div class="chart-panel-accent" style="background:{accent_gradient};"></div>
          <div class="chart-panel-title">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _axis_style(grid: bool, suffix: str = "") -> dict[str, object]:
    style: dict[str, object] = {
        "showgrid": grid,
        "zeroline": False,
        "tickfont": {"size": 10, "color": "#52525b"},
    }
    if grid:
        style["gridcolor"] = "#27272a"
        style["gridwidth"] = 0.5
    if suffix:
        style["ticksuffix"] = suffix
    return style


def _resolve_colors(labels: list[str], color_map: dict[str, str] | None) -> list[str]:
    if not color_map:
        return [_DEFAULT_PALETTE[i % len(_DEFAULT_PALETTE)] for i in range(len(labels))]
    return [
        color_map.get(label, _DEFAULT_PALETTE[i % len(_DEFAULT_PALETTE)])
        for i, label in enumerate(labels)
    ]
