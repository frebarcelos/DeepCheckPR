"""
components/tabs.py — Three tab content renderers: dashboard, explorer, export.
Each render_* function is self-contained and receives only what it needs.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards  # type: ignore[import]

from components.charts import (
    render_bar_chart,
    render_clarity_gauge,
    render_lang_donut,
    render_scatter_chart,
)
from components.kpis import render_kpis
from utils.constants import COL_RENAMES, PREFERRED_COLS
from utils.data import build_report_markdown


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def render_tab_dashboard(df: pd.DataFrame, metrics_active: bool) -> None:
    render_kpis(df, metrics_active)

    # Style metric cards via streamlit-extras
    style_metric_cards(
        background_color="#18181b",
        border_left_color="#6366f1",
        border_color="#27272a",
        box_shadow=False,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col_bar, col_sc = st.columns([3, 2], gap="large")
    with col_bar:
        render_bar_chart(df)
    with col_sc:
        render_scatter_chart(df)

    st.markdown("<br>", unsafe_allow_html=True)

    col_donut, col_gauge = st.columns(2, gap="large")
    with col_donut:
        render_lang_donut(df)
    with col_gauge:
        render_clarity_gauge(df)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXPLORER
# ══════════════════════════════════════════════════════════════════════════════

def render_tab_explorer(df: pd.DataFrame) -> None:
    st.markdown(
        f"<p style='font-size:9px;font-weight:900;text-transform:uppercase;"
        f"letter-spacing:.15em;color:#52525b;margin-bottom:1rem;'>"
        f"▸ Explorador de Registros — {len(df)} resultado(s)</p>",
        unsafe_allow_html=True,
    )

    if len(df) == 0:
        st.info("Nenhum registro corresponde aos filtros.")
        return

    cols  = [c for c in PREFERRED_COLS if c in df.columns]
    extra = [c for c in df.columns if c not in cols]
    disp  = df[cols + extra].rename(columns=COL_RENAMES)

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
        btn_data=df.to_csv(index=False).encode(),
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
        btn_data=df.to_json(orient="records", indent=2).encode(),
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


# ── Private helper ─────────────────────────────────────────────────────────────

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
            f'width:56px;height:56px;display:flex;align-items:center;justify-content:center;'
            f'margin:0 auto 1rem;font-size:24px;">{icon}</div>'
            f'<div class="export-title">{title}</div>'
            f'<div class="export-desc">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            f"⬇ {btn_label}",
            data=btn_data,
            file_name=btn_file,
            mime=btn_mime,
            use_container_width=True,
        )