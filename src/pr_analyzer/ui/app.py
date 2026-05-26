"""
app.py — GitAnalyzer entry point.

Responsibilities (only):
  1. Page configuration
  2. CSS injection
  3. Session-state bootstrap (including the raw_prs tuple from the pipeline)
  4. Sidebar rendering → filter values + LLM toggle
  5. Filtering the active DataFrame (and optionally enriching via dev3+dev4)
  6. Routing to the correct main-area view (empty state OR tabs)

Business logic, UI components, and data transforms live in their respective
modules under components/ and utils/. Functional-pipeline integration lives
in utils.pipeline_bridge (the seam between dev5 and dev1-dev4).
"""

import os

import streamlit as st

# ── Page config (must be the very first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="GitAnalyzer",
    page_icon="🧬",
    layout="wide",
)

# ── Internal imports (after set_page_config) ──────────────────────────────────
from components.sidebar import render_sidebar  # noqa: E402
from components.tabs import (  # noqa: E402
    render_tab_dashboard,
    render_tab_explorer,
    render_tab_export,
)
from utils.constants import APP_NAME, APP_VERSION  # noqa: E402
from utils.data import apply_filters, get_mock_data  # noqa: E402
from utils.pipeline_bridge import (  # noqa: E402
    dataframe_to_prs,
    enrich_prs,
    enriched_to_dataframe,
)
from utils.styles import inject_css  # noqa: E402

from pr_analyzer.llm.client import create_llm_client  # noqa: E402
from pr_analyzer.llm.metrics import ClassificationMetrics  # noqa: E402

# ── CSS ───────────────────────────────────────────────────────────────────────
inject_css()

# ── Session-state bootstrap ───────────────────────────────────────────────────
if "file_loaded" not in st.session_state:
    st.session_state.file_loaded = False
if "fname" not in st.session_state:
    st.session_state.fname = ""
if "df" not in st.session_state:
    st.session_state.df = get_mock_data()
if "llm_backend" not in st.session_state:
    st.session_state.llm_backend = os.environ.get("LLM_BACKEND", "groq")
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = os.environ.get("LLM_MODEL", "llama3")
if "raw_prs" not in st.session_state:
    st.session_state.raw_prs = None
if "llm_cache_stats" not in st.session_state:
    st.session_state.llm_cache_stats = None
if "llm_enriched" not in st.session_state:
    st.session_state.llm_enriched = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
sel_lang, sel_nature, sel_type, sel_clarity, cleaning, llm_tag, metrics = (
    render_sidebar()
)


# ── LLM enrichment (TASK-39) ──────────────────────────────────────────────────
def _maybe_enrich() -> None:
    """Classifica PRs com o LLM configurado. Roda apenas uma vez por dataset carregado."""
    if not llm_tag:
        st.session_state.llm_enriched = False
        return
    if st.session_state.raw_prs is None:
        prs = dataframe_to_prs(st.session_state.df)
        if not prs:
            st.session_state.llm_enriched = False
            st.warning(
                "Classificação LLM requer pelo menos as colunas `id`, `repo` e `lang`. "
                "Faça upload de um CSV compatível ou carregue um dataset local.",
                icon="⚠️",
            )
            return
    else:
        prs = st.session_state.raw_prs

    if st.session_state.llm_enriched:
        return
    n = len(prs)
    backend = st.session_state.get("llm_backend", "groq")
    model = st.session_state.get("ollama_model", os.environ.get("LLM_MODEL", "llama3"))

    os.environ["LLM_BACKEND"] = backend
    os.environ["LLM_MODEL"] = model

    try:
        client = create_llm_client()
    except Exception as exc:
        st.error(f"Erro ao conectar ao {backend.upper()}: {exc}")
        return

    enriched_list = []
    metrics = ClassificationMetrics()

    with st.status(
        f"Classificando {n} PR{'s' if n != 1 else ''} com {backend.upper()}…",
        expanded=True,
    ) as status:
        st.caption(f"Modelo: `{model}`")
        bar = st.progress(0.0)
        for i, ep in enumerate(enrich_prs(prs, client=client, metrics=metrics), 1):
            enriched_list.append(ep)
            bar.progress(i / n)
        status.update(
            label=f"✓ {n} PRs classificados",
            state="complete",
            expanded=False,
        )

    st.session_state.df = enriched_to_dataframe(enriched_list)
    calls_made = n - metrics.cache_hits
    st.session_state.llm_cache_stats = {
        "total": n,
        "cache_hits": metrics.cache_hits,
        "calls_made": calls_made,
    }
    st.session_state.llm_enriched = True


_maybe_enrich()

# ── Filtered DataFrame (pure transform) ───────────────────────────────────────
df = apply_filters(st.session_state.df, sel_lang, sel_nature, sel_type, sel_clarity)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state.file_loaded:
    # ── Empty / landing state ─────────────────────────────────────────────────
    st.markdown(
        """
        <div class="empty-state">
          <div class="empty-icon">📊</div>
          <div class="empty-title">Nenhum dado processado</div>
          <div class="empty-sub">Conecte um dataset para iniciar a análise.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, btn_col, _ = st.columns([2, 1, 2])
    with btn_col:
        if st.button(
            "⚡ Utilizar Dados Demo", use_container_width=True, key="demo_cta"
        ):
            st.session_state.file_loaded = True
            st.session_state.fname = "gh_dataset_2026.csv"
            st.rerun()

else:
    # ── Main tabs ─────────────────────────────────────────────────────────────
    tab_dash, tab_explore, tab_export = st.tabs(["DASH", "EXPLORAR", "EXPORTAR"])

    with tab_dash:
        render_tab_dashboard(df, metrics_active=metrics)

    with tab_explore:
        render_tab_explorer(df)

    with tab_export:
        render_tab_export(df)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<br><p style='text-align:center;font-size:9px;color:#3f3f46;"
    f"font-weight:900;letter-spacing:2px;'>"
    f"{APP_NAME} V{APP_VERSION} — PIPELINE FUNCIONAL</p>",
    unsafe_allow_html=True,
)
