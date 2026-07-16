"""
components/tabs.py — Three tab content renderers: dashboard, explorer, export.

Dashboard tab contains four distribution charts (language, project type,
contribution nature and description clarity) plus scatter and gauge views.

Export tab routes CSV/JSON downloads through `utils.exports`.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from components.charts import (
    render_body_size_chart,
    render_clarity_cross_chart,
    render_clarity_distribution,
    render_clarity_gauge,
    render_lang_distribution,
    render_nature_distribution,
    render_project_type_distribution,
    render_scatter_chart,
)
from components.kpis import render_kpis
from streamlit_extras.metric_cards import style_metric_cards
from utils.constants import COL_RENAMES, PREFERRED_COLS
from utils.data import build_report_markdown
from utils.exports import (
    export_dataframe_csv,
    export_dataframe_json,
)
from utils.pipeline_bridge import (
    distributions_from_dataframe,
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════


def render_tab_dashboard(df: pd.DataFrame, metrics_active: bool) -> None:
    render_kpis(df, metrics_active)

    style_metric_cards(
        background_color="#18181b",
        border_left_color="#6366f1",
        border_color="#27272a",
        box_shadow=False,
    )

    distributions = distributions_from_dataframe(df)

    st.markdown("<br>", unsafe_allow_html=True)
    _render_distribution_row_top(distributions)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_distribution_row_bottom(distributions)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_correlation_row(df)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_analysis_row(df)


def _render_distribution_row_top(distributions: dict[str, dict[str, int]]) -> None:
    col_lang, col_type = st.columns(2, gap="large")
    with col_lang:
        render_lang_distribution(distributions["language"])
    with col_type:
        render_project_type_distribution(distributions["project_type"])


def _render_distribution_row_bottom(
    distributions: dict[str, dict[str, int]],
) -> None:
    col_nature, col_clarity = st.columns(2, gap="large")
    with col_nature:
        render_nature_distribution(distributions["contribution_nature"])
    with col_clarity:
        render_clarity_distribution(distributions["description_clarity"])


def _render_correlation_row(df: pd.DataFrame) -> None:
    col_sc, col_gauge = st.columns(2, gap="large")
    with col_sc:
        render_scatter_chart(df)
    with col_gauge:
        render_clarity_gauge(df)


def _render_analysis_row(df: pd.DataFrame) -> None:
    col_size, col_cross = st.columns(2, gap="large")
    with col_size:
        render_body_size_chart(df)
    with col_cross:
        render_clarity_cross_chart(df)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXPLORER
# ══════════════════════════════════════════════════════════════════════════════


def render_tab_explorer(df: pd.DataFrame) -> None:
    cache_note = _cache_status_note()
    st.markdown(
        f"<p style='font-size:9px;font-weight:900;text-transform:uppercase;"
        f"letter-spacing:.15em;color:#52525b;margin-bottom:1rem;'>"
        f"▸ Explorador de Registros — {len(df)} resultado(s){cache_note}</p>",
        unsafe_allow_html=True,
    )

    if len(df) == 0:
        st.info("Nenhum registro corresponde aos filtros.")
        return

    cols = [c for c in PREFERRED_COLS if c in df.columns]
    extra = [c for c in df.columns if c not in cols]
    disp = df[cols + extra].rename(columns=COL_RENAMES)

    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "Tamanho": st.column_config.ProgressColumn(
                "Tamanho",
                format="%d chars",
                min_value=0,
                max_value=1000,
            ),
            "Natureza (ML)": st.column_config.TextColumn("Natureza (ML)"),
        },
    )


def _cache_status_note() -> str:
    """Render the 'Resultados do cache' indicator next to the explorer header."""
    cache = st.session_state.get("llm_cache_stats")
    if not cache or cache.get("total", 0) == 0:
        return ""
    hits = int(cache.get("cache_hits", 0))
    total = int(cache.get("total", 0))
    if hits == 0:
        return ""
    return f" · <span style='color:#34d399;'>{hits}/{total} resultados do cache</span>"


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — EXPORT
# ══════════════════════════════════════════════════════════════════════════════


def render_tab_export(df: pd.DataFrame) -> None:
    report_md = build_report_markdown(df)
    ec1, ec2, ec3 = st.columns(3, gap="large")

    _export_card(
        col=ec1,
        icon="📊",
        bg="rgba(16,185,129,.15)",
        title="Dataset Estruturado",
        desc="Exportar todos os PRs classificados para CSV.",
        btn_label="Baixar .CSV",
        btn_data=export_dataframe_csv(df),
        btn_file="pr_dataset.csv",
        btn_mime="text/csv",
    )
    _export_card(
        col=ec2,
        icon="🔗",
        bg="rgba(99,102,241,.15)",
        title="Schema de Grafos",
        desc="Representação JSON para Neo4j ou similares.",
        btn_label="Baixar .JSON",
        btn_data=export_dataframe_json(df),
        btn_file="pr_graph_schema.json",
        btn_mime="application/json",
    )
    _export_card(
        col=ec3,
        icon="📄",
        bg="rgba(255,255,255,.06)",
        title="Relatório Executivo",
        desc="Sumário com os KPIs e estatísticas da sessão.",
        btn_label="Baixar .MD",
        btn_data=report_md.encode(),
        btn_file="relatorio.md",
        btn_mime="text/markdown",
    )

    st.markdown(
        """
        <div class="share-banner">
          <div style="display:flex;align-items:center;gap:1rem;">
            <div class="share-circle">🔗</div>
            <div>
              <div class="share-title">Pronto para partilhar?</div>
              <div class="share-sub">Cria um link público e efémero para este dashboard.</div>
            </div>
          </div>
          <div class="share-btn">Gerar Link de Partilha</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Private helper ────────────────────────────────────────────────────────────


def _export_card(
    col: st.delta_generator.DeltaGenerator,
    icon: str,
    bg: str,
    title: str,
    desc: str,
    btn_label: str,
    btn_data: bytes,
    btn_file: str,
    btn_mime: str,
) -> None:
    with col:
        st.markdown(
            f'<div class="export-card">'
            f'<div class="export-icon" style="background:{bg};border-radius:14px;'
            f"width:56px;height:56px;display:flex;align-items:center;justify-content:center;"
            f'margin:0 auto 1rem;font-size:24px;">{icon}</div>'
            f'<div class="export-title">{title}</div>'
            f'<div class="export-desc">{desc}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            f"⬇ {btn_label}",
            data=btn_data,
            file_name=btn_file,
            mime=btn_mime,
            use_container_width=True,
        )
