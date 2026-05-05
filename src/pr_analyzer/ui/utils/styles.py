"""
styles.py — All custom CSS for GitAnalyzer, injected once via inject_css().
Keeping CSS here avoids cluttering app.py and makes theming changes trivial.
"""

import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif;
    background-color: #09090b;
}

/* ── sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #18181b !important;
    border-right: 1px solid #27272a !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem !important; }

[data-testid="stSidebar"] h3 {
    font-size: 10px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #52525b !important;
    margin: 1.25rem 0 0.6rem !important;
}

/* ── metric cards ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 18px;
    padding: 1.25rem 1.5rem !important;
    transition: border-color .2s, box-shadow .2s;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(99,102,241,.4);
    box-shadow: 0 0 0 1px rgba(99,102,241,.15);
}
[data-testid="stMetricLabel"] {
    font-size: 9px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #52525b !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 900 !important;
    letter-spacing: -1px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
[data-testid="stMetricDelta"] { display: none !important; }

/* KPI colours by position */
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(1) [data-testid="stMetricValue"] { color: #818cf8 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(2) [data-testid="stMetricValue"] { color: #34d399 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(3) [data-testid="stMetricValue"] { color: #fbbf24 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(4) [data-testid="stMetricValue"] { color: #a1a1aa !important; }

/* ── tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: transparent;
    border-bottom: 1px solid #27272a;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    font-size: 11px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #52525b !important;
    padding: 0 1.5rem !important;
    transition: color .15s;
}
.stTabs [aria-selected="true"] {
    color: #818cf8 !important;
    border-bottom: 2px solid #818cf8 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.75rem !important; }

/* ── buttons ────────────────────────────────────────────────────────────── */
.stButton > button {
    background: #6366f1 !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 10px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 0.65rem 1.25rem !important;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: #4f46e5 !important;
    transform: translateY(-1px);
    box-shadow: 0 8px 20px -4px rgba(99,102,241,0.4) !important;
}

/* ── download buttons ───────────────────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
    background: #27272a !important;
    color: #d4d4d8 !important;
    border: 1px solid #3f3f46 !important;
    border-radius: 12px !important;
    font-size: 9px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    width: 100% !important;
    transition: all 0.15s !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #6366f1 !important;
    color: white !important;
    border-color: #6366f1 !important;
}

/* ── file uploader ──────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] section {
    background: #27272a !important;
    border: 1.5px dashed #3f3f46 !important;
    border-radius: 14px !important;
    transition: border-color .15s;
}
[data-testid="stFileUploader"] section:hover { border-color: #6366f1 !important; }
[data-testid="stFileUploadDropzone"] * { font-size: 10px !important; color: #71717a !important; }

/* ── selectbox ──────────────────────────────────────────────────────────── */
div[data-baseweb="select"] > div {
    background: #27272a !important;
    border: 1px solid #3f3f46 !important;
    border-radius: 10px !important;
    font-size: 12px !important;
}

/* ── toggles ────────────────────────────────────────────────────────────── */
[data-testid="stToggle"] {
    background: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 12px;
    padding: 0.65rem 0.9rem;
    margin-bottom: 0.4rem;
}
[data-testid="stToggle"] label p {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #d4d4d8 !important;
}

/* ── dataframe ──────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #27272a !important;
    border-radius: 18px !important;
    overflow: hidden;
}

/* ── sidebar widget labels ──────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 9px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #52525b !important;
}
[data-testid="stSidebar"] hr { border-color: #27272a !important; }

/* ── status badge (file-ok) ──────────────────────────────────────────────── */
.file-ok {
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 0.75rem;
    animation: fadeSlide .3s ease;
}
.file-ok-icon {
    width: 34px; height: 34px; border-radius: 9px;
    background: rgba(16,185,129,0.15);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0;
}
.file-ok-name  { font-size: 10px; font-weight: 800; color: #d4d4d8; font-family: 'JetBrains Mono', monospace; }
.file-ok-label { font-size: 9px; font-weight: 700; color: #34d399; text-transform: uppercase; letter-spacing: 0.1em; }

/* ── chart panels ────────────────────────────────────────────────────────── */
.chart-panel {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 22px;
    padding: 1.5rem 1.5rem 0.5rem;
    position: relative; overflow: hidden;
}
.chart-panel-accent {
    position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #6366f1, #a78bfa);
}
.chart-panel-title {
    font-size: 9px; font-weight: 900;
    text-transform: uppercase; letter-spacing: 0.16em;
    color: #52525b; margin-bottom: 0.75rem;
    display: flex; align-items: center; gap: 6px;
}

/* ── export cards ────────────────────────────────────────────────────────── */
.export-card {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 22px;
    padding: 2rem 1.5rem;
    text-align: center;
    transition: border-color .2s, transform .2s, box-shadow .2s;
    height: 100%;
}
.export-card:hover {
    border-color: rgba(99,102,241,.4);
    transform: translateY(-3px);
    box-shadow: 0 12px 32px -8px rgba(99,102,241,.2);
}
.export-icon  { font-size: 28px; margin-bottom: 1rem; }
.export-title { font-size: 13px; font-weight: 900; color: #f4f4f5; margin-bottom: 6px; }
.export-desc  { font-size: 10px; color: #71717a; line-height: 1.6; margin-bottom: 1.25rem; }

/* ── share banner ────────────────────────────────────────────────────────── */
.share-banner {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    border-radius: 22px;
    padding: 2rem; margin-top: 1.5rem;
    display: flex; align-items: center;
    justify-content: space-between; gap: 1rem;
    box-shadow: 0 20px 40px -10px rgba(99,102,241,.4);
}
.share-circle {
    width: 50px; height: 50px; border-radius: 50%;
    background: rgba(255,255,255,.18);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; flex-shrink: 0;
}
.share-title { font-size: 17px; font-weight: 900; color: white; letter-spacing: -0.3px; }
.share-sub   { font-size: 10px; color: rgba(255,255,255,.65); margin-top: 3px; }
.share-btn   {
    background: white; color: #6366f1;
    border-radius: 14px; padding: 0.8rem 1.75rem;
    font-size: 9px; font-weight: 900;
    text-transform: uppercase; letter-spacing: 0.14em;
    white-space: nowrap; flex-shrink: 0; cursor: pointer;
    transition: transform .15s, box-shadow .15s;
}
.share-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,.2);
}

/* ── empty state ─────────────────────────────────────────────────────────── */
.empty-state {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    min-height: 70vh; text-align: center;
}
.empty-icon  { font-size: 72px; opacity: 0.1; margin-bottom: 1rem; }
.empty-title { font-size: 20px; font-weight: 900; color: #52525b; margin-bottom: 0.5rem; }
.empty-sub   { font-size: 12px; color: #3f3f46; margin-bottom: 2rem; }

/* ── animations ──────────────────────────────────────────────────────────── */
@keyframes fadeSlide {
    from { opacity: 0; transform: translateY(-6px); }
    to   { opacity: 1; transform: translateY(0);    }
}

/* ── main padding ────────────────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"] { padding: 2rem 2.5rem !important; }
"""


def inject_css() -> None:
    """Inject the global CSS stylesheet into the Streamlit page."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
