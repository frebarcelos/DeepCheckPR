"""
GitAnalyzer — UI module (Streamlit)
Módulo de efeito colateral: interação com o usuário via Streamlit.
"""

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GitAnalyzer",
    page_icon="🧬",
    layout="wide",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif;
    background-color: #09090b;
}

/* ── hide streamlit chrome ── */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {
    display: none !important;
}

/* ── sidebar ── */
[data-testid="stSidebar"] {
    background-color: #18181b !important;
    border-right: 1px solid #27272a !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem !important; }

/* ── sidebar section headers ── */
[data-testid="stSidebar"] h3 {
    font-size: 10px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #52525b !important;
    margin: 1.25rem 0 0.6rem !important;
}

/* ── metric cards ── */
[data-testid="stMetric"] {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 18px;
    padding: 1.25rem 1.5rem !important;
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
}
[data-testid="stMetricDelta"] { display: none !important; }

/* KPI colours by position */
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(1) [data-testid="stMetricValue"] { color: #818cf8 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(2) [data-testid="stMetricValue"] { color: #34d399 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(3) [data-testid="stMetricValue"] { color: #fbbf24 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(4) [data-testid="stMetricValue"] { color: #a1a1aa !important; }

/* ── tabs ── */
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
}
.stTabs [aria-selected="true"] {
    color: #818cf8 !important;
    border-bottom: 2px solid #818cf8 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.75rem !important; }

/* ── primary buttons ── */
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

/* ── download buttons ── */
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

/* ── file uploader ── */
[data-testid="stFileUploader"] section {
    background: #27272a !important;
    border: 1.5px dashed #3f3f46 !important;
    border-radius: 14px !important;
}
[data-testid="stFileUploadDropzone"] * { font-size: 10px !important; color: #71717a !important; }

/* ── selectbox ── */
div[data-baseweb="select"] > div {
    background: #27272a !important;
    border: 1px solid #3f3f46 !important;
    border-radius: 10px !important;
    font-size: 12px !important;
}

/* ── toggles ── */
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

/* ── dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #27272a !important;
    border-radius: 18px !important;
    overflow: hidden;
}

/* ── sidebar widget label ── */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 9px !important;
    font-weight: 900 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #52525b !important;
}
[data-testid="stSidebar"] hr { border-color: #27272a !important; }

/* ── success box ── */
.file-ok {
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 0.75rem;
}
.file-ok-icon {
    width: 34px; height: 34px; border-radius: 9px;
    background: rgba(16,185,129,0.15);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0;
}
.file-ok-name  { font-size: 10px; font-weight: 800; color: #d4d4d8; }
.file-ok-label { font-size: 9px; font-weight: 700; color: #34d399; text-transform: uppercase; letter-spacing: 0.1em; }

/* ── chart panels ── */
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
    background: #6366f1;
}
.chart-panel-title {
    font-size: 9px; font-weight: 900;
    text-transform: uppercase; letter-spacing: 0.16em;
    color: #52525b; margin-bottom: 0.75rem;
    display: flex; align-items: center; gap: 6px;
}

/* ── export cards ── */
.export-card {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 22px;
    padding: 2rem 1.5rem;
    text-align: center;
    transition: border-color 0.2s;
    height: 100%;
}
.export-card:hover { border-color: rgba(99,102,241,0.4); }
.export-icon { font-size: 28px; margin-bottom: 1rem; }
.export-title { font-size: 13px; font-weight: 900; color: #f4f4f5; margin-bottom: 6px; }
.export-desc  { font-size: 10px; color: #71717a; line-height: 1.6; margin-bottom: 1.25rem; }

/* ── share banner ── */
.share-banner {
    background: #6366f1; border-radius: 22px;
    padding: 2rem; margin-top: 1.5rem;
    display: flex; align-items: center;
    justify-content: space-between; gap: 1rem;
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
}

/* ── empty state ── */
.empty-state {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    min-height: 70vh; text-align: center;
}
.empty-icon  { font-size: 72px; opacity: 0.1; margin-bottom: 1rem; }
.empty-title { font-size: 20px; font-weight: 900; color: #52525b; margin-bottom: 0.5rem; }
.empty-sub   { font-size: 12px; color: #3f3f46; margin-bottom: 2rem; }

/* ── main padding ── */
[data-testid="stMainBlockContainer"] { padding: 2rem 2.5rem !important; }
</style>
""", unsafe_allow_html=True)

# ─── Mock data (pure — sem I/O, sem estado global mutável) ───────────────────
@st.cache_data
def get_mock_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"id":1,"lang":"Python",    "type":"Library",  "nature":"Bug Fix",      "clarity":"Excellent",   "size":450,"repo":"pandas",      "date":"2024-03-01"},
        {"id":2,"lang":"JavaScript","type":"Framework", "nature":"Feature",      "clarity":"Basic",       "size":120,"repo":"next.js",     "date":"2024-03-02"},
        {"id":3,"lang":"Go",        "type":"CLI Tool",  "nature":"Refactor",     "clarity":"Good",        "size":300,"repo":"terraform",   "date":"2024-03-02"},
        {"id":4,"lang":"Python",    "type":"Library",  "nature":"Feature",      "clarity":"Good",        "size":800,"repo":"scikit-learn","date":"2024-03-03"},
        {"id":5,"lang":"TypeScript","type":"Web App",   "nature":"Documentation","clarity":"Insufficient","size":50, "repo":"vscode",     "date":"2024-03-04"},
        {"id":6,"lang":"Java",      "type":"Framework", "nature":"Bug Fix",      "clarity":"Excellent",   "size":600,"repo":"spring",     "date":"2024-03-05"},
    ])

CLARITY_ORDER = ["Excellent","Good","Basic","Insufficient"]
NATURE_COLOR  = {"Bug Fix":"#818cf8","Feature":"#34d399","Refactor":"#fbbf24","Documentation":"#a78bfa"}
CLARITY_COLOR = {"Excellent":"#34d399","Good":"#818cf8","Basic":"#fbbf24","Insufficient":"#f87171"}

PLOT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#52525b", size=10),
    margin=dict(l=4, r=4, t=8, b=4),
    height=280,
)

# ─── Session state ────────────────────────────────────────────────────────────
if "file_loaded" not in st.session_state:
    st.session_state.file_loaded = False   # True = user uploaded OR clicked demo
if "fname" not in st.session_state:
    st.session_state.fname = ""
if "df" not in st.session_state:
    st.session_state.df = get_mock_data()

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── Brand ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='display:flex;align-items:center;gap:10px;margin-bottom:1.5rem;padding:0 0.25rem;'>
      <div style='background:#4f46e5;width:30px;height:30px;border-radius:8px;
                  display:flex;align-items:center;justify-content:center;font-size:14px;'>🔧</div>
      <span style='font-size:18px;font-weight:900;color:#f4f4f5;letter-spacing:-0.5px;'>GitAnalyzer</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Dados de Entrada ──────────────────────────────────────────────────────
    st.markdown("### 🗄 DADOS DE ENTRADA")

    uploaded = st.file_uploader(
        "CSV / JSON", type=["csv","json"], label_visibility="collapsed",
    )

    if uploaded is not None:
        try:
            if uploaded.name.endswith(".json"):
                st.session_state.df = pd.DataFrame(json.load(uploaded))
            else:
                st.session_state.df = pd.read_csv(uploaded)
            st.session_state.file_loaded = True
            st.session_state.fname = uploaded.name
        except Exception as exc:  # noqa: BLE001
            st.error(f"Erro: {exc}")

    if st.session_state.file_loaded:
        fname = st.session_state.fname or "gh_dataset_2026.csv"
        st.markdown(f"""
        <div class="file-ok">
          <div class="file-ok-icon">✓</div>
          <div>
            <div class="file-ok-name">{fname}</div>
            <div class="file-ok-label">Sincronizado</div>
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button("REMOVER FONTE", key="rm", width="stretch"):
            st.session_state.df = get_mock_data()
            st.session_state.file_loaded = False
            st.session_state.fname = ""
            st.rerun()
    else:
        st.markdown("<p style='font-size:10px;color:#52525b;font-weight:700;text-align:center;margin:.5rem 0;'>NENHUM DATASET ATIVO</p>", unsafe_allow_html=True)

    st.divider()

    # ── Pipeline ──────────────────────────────────────────────────────────────
    st.markdown("### ⚙ PIPELINE")
    cleaning = st.toggle("Sanitização Funcional", value=True,  key="cleaning")
    llm_tag  = st.toggle("Classificação LLM",     value=True,  key="llm")
    metrics  = st.toggle("Geração de Métricas",   value=False, key="metrics")

    st.divider()

    # ── Filtros ───────────────────────────────────────────────────────────────
    st.markdown("### 🔍 REFINAR VISÃO")
    df_all = st.session_state.df
    langs   = ["Todas"] + sorted(df_all["lang"].dropna().unique().tolist())   if "lang"   in df_all.columns else ["Todas"]
    natures = ["Todas"] + sorted(df_all["nature"].dropna().unique().tolist()) if "nature" in df_all.columns else ["Todas"]

    sel_lang   = st.selectbox("LINGUAGEM", langs)
    sel_nature = st.selectbox("NATUREZA",  natures)

# ─── Filter (pure transform — sem efeitos colaterais) ────────────────────────
df: pd.DataFrame = st.session_state.df.copy()
if sel_lang   != "Todas" and "lang"   in df.columns: df = df[df["lang"]   == sel_lang]
if sel_nature != "Todas" and "nature" in df.columns: df = df[df["nature"] == sel_nature]

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════════════════════

if not st.session_state.file_loaded:
    # ── Empty state ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">📊</div>
      <div class="empty-title">Nenhum dado processado</div>
      <div class="empty-sub">Conecte um dataset para iniciar a análise.</div>
    </div>""", unsafe_allow_html=True)

    _, btn_col, _ = st.columns([2,1,2])
    with btn_col:
        if st.button("⚡ Utilizar Dados Demo", use_container_width=True, key="demo_cta"):
            st.session_state.file_loaded = True
            st.session_state.fname = "gh_dataset_2026.csv"
            st.rerun()

else:
    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_dash, tab_explore, tab_export = st.tabs(["DASH", "EXPLORAR", "EXPORTAR"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — DASH
    # ══════════════════════════════════════════════════════════════════════════
    with tab_dash:
        # KPIs
        k1, k2, k3, k4 = st.columns(4, gap="small")
        k1.metric("● PRs Processados", len(df))
        k2.metric("● Clareza (LLM)", "Nível B+")
        k3.metric("● Volatilidade", "Baixa")
        k4.metric("● Cache Agno", "Ativo" if st.session_state.metrics else "Inativo")

        st.markdown("<br>", unsafe_allow_html=True)

        col_bar, col_sc = st.columns([3,2], gap="large")

        # Bar chart
        with col_bar:
            st.markdown("""
            <div class="chart-panel">
              <div class="chart-panel-accent"></div>
              <div class="chart-panel-title">📊 Classificação Semântica de Contribuições</div>
            </div>""", unsafe_allow_html=True)
            if "nature" in df.columns and len(df):
                nc = df["nature"].value_counts().reset_index()
                nc.columns = ["Natureza","Qtd"]
                fig_bar = go.Figure(go.Bar(
                    x=nc["Natureza"], y=nc["Qtd"],
                    marker_color=[NATURE_COLOR.get(n,"#818cf8") for n in nc["Natureza"]],
                    marker_line_width=0,
                ))
                fig_bar.update_layout(
                    **PLOT_BASE, showlegend=False, bargap=0.35,
                    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#52525b")),
                    yaxis=dict(showgrid=True, gridcolor="#27272a", zeroline=False, tickfont=dict(size=10, color="#52525b"), gridwidth=0.5),
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar":False})
            else:
                st.info("Sem dados para exibir.")

        # Scatter
        with col_sc:
            st.markdown("""
            <div class="chart-panel">
              <div class="chart-panel-title">📄 Correlação: Qualidade vs Escopo</div>
            </div>""", unsafe_allow_html=True)
            if {"size","clarity","repo"}.issubset(df.columns) and len(df):
                fig_sc = px.scatter(
                    df, x="size", y="clarity",
                    color="clarity", hover_data=["repo","lang"],
                    color_discrete_map=CLARITY_COLOR,
                    category_orders={"clarity": CLARITY_ORDER},
                    labels={"size":"","clarity":""},
                )
                fig_sc.update_layout(
                    **PLOT_BASE, showlegend=False,
                    xaxis=dict(showgrid=False, zeroline=False,
                               ticksuffix=" chars", tickfont=dict(size=9, color="#52525b")),
                    yaxis=dict(showgrid=True, gridcolor="#27272a", gridwidth=0.5,
                               zeroline=False, tickfont=dict(size=9, color="#52525b")),
                )
                fig_sc.update_traces(marker=dict(size=13, opacity=0.8, line=dict(width=0)))
                st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar":False})
            else:
                st.info("Sem dados para exibir.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — EXPLORAR
    # ══════════════════════════════════════════════════════════════════════════
    with tab_explore:
        st.markdown(
            f"<p style='font-size:9px;font-weight:900;text-transform:uppercase;"
            f"letter-spacing:.15em;color:#52525b;margin-bottom:1rem;'>"
            f"▸ Explorador de Registros — {len(df)} resultado(s)</p>",
            unsafe_allow_html=True,
        )
        if len(df):
            preferred = ["date","repo","lang","type","nature","clarity","size"]
            cols      = [c for c in preferred if c in df.columns]
            extra     = [c for c in df.columns if c not in cols]
            disp      = df[cols+extra].rename(columns={
                "date":"Data","repo":"Repositório","lang":"Linguagem",
                "type":"Tipo","nature":"Natureza (ML)","clarity":"Status LLM","size":"Tamanho",
            })
            st.dataframe(
                disp, use_container_width=True, hide_index=True, height=500,
                column_config={
                    "Tamanho": st.column_config.ProgressColumn(
                        "Tamanho", format="%d chars", min_value=0, max_value=1000,
                    ),
                    "Natureza (ML)": st.column_config.TextColumn("Natureza (ML)"),
                },
            )
        else:
            st.info("Nenhum registro corresponde aos filtros.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — EXPORTAR
    # ══════════════════════════════════════════════════════════════════════════
    with tab_export:
        nat_lines = ""
        if "nature" in df.columns and len(df):
            nat_lines = "\n".join(f"- {n}: {c}" for n,c in df["nature"].value_counts().items())
        report_md = (
            "# GitAnalyzer — Relatório Executivo\n\n"
            f"**PRs Processados:** {len(df)}\n"
            f"**Linguagem Top:** {df['lang'].mode()[0] if len(df) else '—'}\n\n"
            f"## Distribuição por Natureza\n{nat_lines}"
        )

        ec1, ec2, ec3 = st.columns(3, gap="large")

        def _card(col, icon, bg, title, desc, btn_label, btn_data, btn_file, btn_mime):  # noqa: PLR0913
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
                    f"⬇ {btn_label}", data=btn_data,
                    file_name=btn_file, mime=btn_mime,
                    use_container_width=True,
                )

        _card(ec1,"📊","rgba(16,185,129,.15)","Dataset Estruturado",
              "Exportar todos os PRs classificados para CSV.",
              "Baixar .CSV", df.to_csv(index=False).encode(), "pr_dataset.csv","text/csv")

        _card(ec2,"🔗","rgba(99,102,241,.15)","Schema de Grafos",
              "Representação JSON para Neo4j ou similares.",
              "Baixar .JSON", df.to_json(orient="records",indent=2).encode(),
              "pr_graph_schema.json","application/json")

        _card(ec3,"📄","rgba(255,255,255,.06)","Relatório Executivo",
              "Sumário com os KPIs e estatísticas da sessão.",
              "Baixar .MD", report_md.encode(), "relatorio.md","text/markdown")

        st.markdown("""
        <div class="share-banner">
          <div style="display:flex;align-items:center;gap:1rem;">
            <div class="share-circle">🔗</div>
            <div>
              <div class="share-title">Pronto para partilhar?</div>
              <div class="share-sub">Cria um link público e efémero para este dashboard.</div>
            </div>
          </div>
          <div class="share-btn">Gerar Link de Partilha</div>
        </div>""", unsafe_allow_html=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    "<br><p style='text-align:center;font-size:9px;color:#3f3f46;"
    "font-weight:900;letter-spacing:2px;'>GITANALYZER V2.0 — PIPELINE FUNCIONAL</p>",
    unsafe_allow_html=True,
)