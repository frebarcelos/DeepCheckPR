"""
components/sidebar.py — Sidebar with branding, data source, pipeline toggles, and filters.
Returns filter selections so app.py stays decoupled from widget state.
"""

from __future__ import annotations

import streamlit as st
from utils.data import get_filter_options, get_mock_data, load_dataframe


def render_sidebar() -> tuple[str, str, bool, bool, bool]:
    """
    Render the full sidebar and return:
        (sel_lang, sel_nature, cleaning, llm_tag, metrics)
    Handles file upload and demo-data state internally.
    """
    with st.sidebar:
        _render_brand()
        _render_data_section()
        st.divider()
        cleaning, llm_tag, metrics = _render_pipeline()
        st.divider()
        sel_lang, sel_nature = _render_filters()

    return sel_lang, sel_nature, cleaning, llm_tag, metrics


# ── Private helpers ───────────────────────────────────────────────────────────


def _render_brand() -> None:
    st.markdown(
        """
        <div style='display:flex;align-items:center;gap:10px;
                    margin-bottom:1.5rem;padding:0 0.25rem;'>
          <div style='background:#4f46e5;width:30px;height:30px;border-radius:8px;
                      display:flex;align-items:center;justify-content:center;font-size:14px;'>
            🔧
          </div>
          <span style='font-size:18px;font-weight:900;color:#f4f4f5;letter-spacing:-0.5px;'>
            GitAnalyzer
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_data_section() -> None:
    st.markdown("### 🗄 DADOS DE ENTRADA")

    uploaded = st.file_uploader(
        "CSV / JSON",
        type=["csv", "json"],
        label_visibility="collapsed",
    )

    if uploaded is not None:
        try:
            st.session_state.df = load_dataframe(uploaded, uploaded.name)
            st.session_state.file_loaded = True
            st.session_state.fname = uploaded.name
        except ValueError as exc:
            st.error(str(exc))

    if st.session_state.file_loaded:
        fname = st.session_state.fname or "gh_dataset_2026.csv"
        st.markdown(
            f"""
            <div class="file-ok">
              <div class="file-ok-icon">✓</div>
              <div>
                <div class="file-ok-name">{fname}</div>
                <div class="file-ok-label">Sincronizado</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("REMOVER FONTE", key="rm", use_container_width=True):
            st.session_state.df = get_mock_data()
            st.session_state.file_loaded = False
            st.session_state.fname = ""
            st.rerun()
    else:
        st.markdown(
            "<p style='font-size:10px;color:#52525b;font-weight:700;"
            "text-align:center;margin:.5rem 0;'>NENHUM DATASET ATIVO</p>",
            unsafe_allow_html=True,
        )


def _render_pipeline() -> tuple[bool, bool, bool]:
    st.markdown("### ⚙ PIPELINE")
    cleaning = st.toggle("Sanitização Funcional", value=True, key="cleaning")
    llm_tag = st.toggle("Classificação LLM", value=True, key="llm")
    metrics = st.toggle("Geração de Métricas", value=False, key="metrics")
    return cleaning, llm_tag, metrics


def _render_filters() -> tuple[str, str]:
    st.markdown("### 🔍 REFINAR VISÃO")
    langs, natures = get_filter_options(st.session_state.df)
    sel_lang = st.selectbox("LINGUAGEM", langs)
    sel_nature = st.selectbox("NATUREZA", natures)
    return sel_lang, sel_nature
