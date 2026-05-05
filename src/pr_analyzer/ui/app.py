"""
app.py — GitAnalyzer entry point.

Responsibilities (only):
  1. Page configuration
  2. CSS injection
  3. Session-state bootstrap
  4. Sidebar rendering → filter values
  5. Filtering the active DataFrame
  6. Routing to the correct main-area view (empty state OR tabs)

All business logic, UI components, and data transforms live in their
respective modules under components/ and utils/.
"""

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
from utils.styles import inject_css  # noqa: E402

# ── CSS ───────────────────────────────────────────────────────────────────────
inject_css()

# ── Session-state bootstrap ───────────────────────────────────────────────────
if "file_loaded" not in st.session_state:
    st.session_state.file_loaded = False
if "fname" not in st.session_state:
    st.session_state.fname = ""
if "df" not in st.session_state:
    st.session_state.df = get_mock_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
sel_lang, sel_nature, cleaning, llm_tag, metrics = render_sidebar()

# ── Filtered DataFrame (pure transform) ───────────────────────────────────────
df = apply_filters(st.session_state.df, sel_lang, sel_nature)

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
