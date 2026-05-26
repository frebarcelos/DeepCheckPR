"""
components/sidebar.py — Sidebar with branding, data source, LLM backend, pipeline toggles,
and filters. Returns filter selections so app.py stays decoupled from widget state.

The "Classificação LLM" toggle (TASK-39) controls whether `enrich_prs` is
applied to PRRecords coming from the functional pipeline. The result is
surfaced back through st.session_state.llm_cache_stats so the explorer tab
can show the "resultados do cache" indicator.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import streamlit as st
from utils.data import (
    check_ollama,
    discover_datasets,
    get_filter_options,
    get_mock_data,
    load_archive_sample,
    load_dataframe,
)
from utils.pipeline_bridge import (
    load_uploaded,
)

# Escalas de carregamento: (label_ui, max_records, estimativa_groq, estimativa_ollama)
# Groq free + tools + batch=5: ~150 PR/min  |  Ollama qwen2:1.5b 4w: ~80 PR/min
_RECORD_SCALES: tuple[tuple[str, int, str, str], ...] = (
    ("500  (amostra rapida)", 500, "~3 min", "~6 min"),
    ("2 000  (demo padrao)", 2_000, "~13 min", "~25 min"),
    ("10 000  (analise)", 10_000, "~1 h", "~2 h"),
    ("50 000  (corpus parcial)", 50_000, "~6 h", "~10 h"),
)


def render_sidebar() -> tuple[str, str, str, str, bool, bool, bool]:
    """
    Render the full sidebar and return:
        (sel_lang, sel_nature, sel_type, sel_clarity, cleaning, llm_tag, metrics)
    Handles file upload, local dataset selection, and LLM backend state internally.
    """
    with st.sidebar:
        _render_brand()
        _render_data_section()
        st.divider()
        _render_llm_backend()
        st.divider()
        cleaning, llm_tag, metrics = _render_pipeline()
        st.divider()
        sel_lang, sel_nature, sel_type, sel_clarity = _render_filters()

    return sel_lang, sel_nature, sel_type, sel_clarity, cleaning, llm_tag, metrics


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
        _handle_upload(uploaded)

    _render_local_datasets()
    _render_file_status()


def _render_file_status() -> None:
    if st.session_state.file_loaded:
        fname = st.session_state.fname or "dataset"
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
            st.session_state.raw_prs = None
            st.session_state.llm_cache_stats = None
            st.session_state.llm_enriched = False
            st.rerun()
    else:
        st.markdown(
            "<p style='font-size:10px;color:#52525b;font-weight:700;"
            "text-align:center;margin:.5rem 0;'>NENHUM DATASET ATIVO</p>",
            unsafe_allow_html=True,
        )


def _handle_upload(uploaded: object) -> None:
    """Route uploaded CSVs through the functional pipeline when possible."""
    filename = getattr(uploaded, "name", "uploaded.csv")
    try:
        if filename.endswith(".csv"):
            df, prs = load_uploaded(uploaded, filename)
            st.session_state.df = df
            st.session_state.raw_prs = prs
        else:
            st.session_state.df = load_dataframe(uploaded, filename)
            st.session_state.raw_prs = None
        st.session_state.file_loaded = True
        st.session_state.fname = filename
        st.session_state.llm_cache_stats = None
        st.session_state.llm_enriched = False
    except ValueError as exc:
        st.error(str(exc))


def _render_local_datasets() -> None:
    datasets = discover_datasets("data")
    if not datasets:
        return

    with st.expander("DATASETS LOCAIS", expanded=False):
        scale_labels: tuple[str, ...] = tuple(lbl for lbl, *_ in _RECORD_SCALES)
        scale_choice: str = st.selectbox(
            "Escala de registros",
            scale_labels,
            index=1,
            key="record_scale",
        )
        _, max_records, est_groq, est_ollama = next(
            t for t in _RECORD_SCALES if t[0] == scale_choice
        )
        st.caption(f"LLM: ~{est_groq} Groq+tools  |  ~{est_ollama} Ollama 4w")

        labels: list[str] = [
            "— selecionar —",
            "Todas as bases",
            *(d["label"] for d in datasets),
        ]
        choice: str = st.selectbox(
            "Dataset local",
            labels,
            key="local_ds_select",
            label_visibility="collapsed",
        )
        if choice != "— selecionar —" and st.button(
            "Carregar", key="load_local_btn", use_container_width=True
        ):
            if choice == "Todas as bases":
                _load_all_datasets(datasets, max_records)
            else:
                selected = next(d for d in datasets if d["label"] == choice)
                _load_local(selected, max_records)


def _load_local(dataset: dict[str, Any], max_records: int = 2000) -> None:
    fmt: str = dataset["format"]
    path: str = dataset["path"]

    raw_prs = None
    if fmt == "archive":
        lang = str(dataset.get("lang", ""))
        label = (
            "todos os registros" if max_records == 0 else f"{max_records:,} registros"
        )
        with st.spinner(f"Carregando {lang} ({label})…"):
            df = load_archive_sample(path, lang, max_records)
    elif fmt == "csv":
        import io as _io

        with open(path, "rb") as f:
            raw = f.read()
        df, raw_prs = load_uploaded(_io.BytesIO(raw), path.split("/")[-1])
        if raw_prs is None:
            df = pd.read_csv(_io.BytesIO(raw))
    else:
        with open(path, encoding="utf-8") as jf:
            raw_json = json.load(jf)
        if isinstance(raw_json, dict):
            df = load_archive_sample(
                path, lang=dataset.get("lang") or "", max_records=max_records
            )
        else:
            df = pd.DataFrame(raw_json)

    st.session_state.df = df
    st.session_state.raw_prs = raw_prs
    st.session_state.file_loaded = True
    st.session_state.fname = dataset["label"]
    st.session_state.llm_enriched = False
    st.session_state.llm_cache_stats = None
    st.rerun()


def _load_all_datasets(datasets: list[dict[str, Any]], max_records: int = 2000) -> None:
    frames: list[pd.DataFrame] = []
    label = "todos os registros" if max_records == 0 else f"{max_records:,} por base"
    with st.spinner(f"Carregando todas as bases ({label})…"):
        for ds in datasets:
            fmt: str = ds["format"]
            path: str = ds["path"]
            if fmt in ("archive", "json"):
                lang = str(ds.get("lang", ""))
                frames.append(load_archive_sample(path, lang, max_records))
            elif fmt == "csv":
                import io as _io

                with open(path, "rb") as f:
                    raw = f.read()
                df_csv, _ = load_uploaded(_io.BytesIO(raw), path.split("/")[-1])
                frames.append(df_csv)

    if not frames:
        return

    combined = pd.concat(frames, ignore_index=True)
    st.session_state.df = combined
    st.session_state.raw_prs = None
    st.session_state.file_loaded = True
    st.session_state.fname = "Todas as bases"
    st.session_state.llm_enriched = False
    st.session_state.llm_cache_stats = None
    st.rerun()


# ── LLM backend ───────────────────────────────────────────────────────────────


def _render_llm_backend() -> None:
    st.markdown("### 🤖 BACKEND LLM")

    current = st.session_state.get("llm_backend", "groq")
    backend: str = st.radio(
        "Backend",
        ["groq", "ollama"],
        format_func=lambda x: "Groq  (API)" if x == "groq" else "Ollama  (local)",
        index=0 if current == "groq" else 1,
        horizontal=True,
        label_visibility="collapsed",
        key="llm_backend_radio",
    )
    st.session_state.llm_backend = backend

    if backend == "groq":
        _render_groq_panel()
    else:
        _render_ollama_panel()


def _render_groq_panel() -> None:
    key = os.environ.get("GROQ_API_KEY", "")
    if key and not key.startswith("gsk_your"):
        st.markdown(
            "<p style='font-size:10px;color:#34d399;font-weight:700;margin:.4rem 0;'>"
            "✓ API key configurada</p>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("Configure GROQ_API_KEY no .env")


def _render_ollama_panel() -> None:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    st.caption(f"Host: `{host}`")

    should_check = st.session_state.get("ollama_checked") is None
    if st.button("↺  Verificar conexão", key="ollama_verify") or should_check:
        running, models = check_ollama(host)
        st.session_state.ollama_running = running
        st.session_state.ollama_models = models
        st.session_state.ollama_checked = True

    if st.session_state.get("ollama_running"):
        st.markdown(
            "<p style='font-size:10px;color:#34d399;font-weight:700;margin:.4rem 0;'>"
            "✓ Conectado</p>",
            unsafe_allow_html=True,
        )
        cached_models: list[str] = st.session_state.get("ollama_models", [])
        if cached_models:
            chosen: str = st.selectbox(
                "Modelo", cached_models, key="ollama_model_select"
            )
            st.session_state.ollama_model = chosen
        else:
            st.caption("Nenhum modelo instalado.")
            st.code("ollama pull llama3", language="bash")
    else:
        st.error("Ollama não encontrado")
        _render_ollama_setup(host)


def _render_ollama_setup(host: str) -> None:
    st.markdown(
        "<p style='font-size:10px;font-weight:700;color:#a1a1aa;margin:.5rem 0 .25rem;'>"
        "Como configurar:</p>",
        unsafe_allow_html=True,
    )
    st.markdown("1. Instale em **ollama.com**")
    st.markdown("2. Baixe um modelo:")
    st.code("ollama pull llama3", language="bash")
    st.markdown("3. Inicie o servidor:")
    st.code("ollama serve", language="bash")
    if "host.docker.internal" not in host and "localhost" in host:
        st.info(
            "No Docker, defina no `.env`:\n"
            "`OLLAMA_HOST=http://host.docker.internal:11434`"
        )


# ── Pipeline toggles ──────────────────────────────────────────────────────────


def _render_pipeline() -> tuple[bool, bool, bool]:
    st.markdown("### ⚙ PIPELINE")
    cleaning = st.toggle("Sanitização Funcional", value=True, key="cleaning")
    llm_tag = st.toggle("Ativar Classificação LLM", value=False, key="llm")
    metrics = st.toggle("Geração de Métricas", value=False, key="metrics")
    _render_cache_indicator()
    return cleaning, llm_tag, metrics


def _render_cache_indicator() -> None:
    """Surface cache-hit info coming back from the last enrichment run."""
    cache = st.session_state.get("llm_cache_stats") or {}
    total = int(cache.get("total", 0))
    if total == 0:
        return
    hits = int(cache.get("cache_hits", 0))
    misses = int(cache.get("calls_made", 0))
    badge_color = "#34d399" if hits else "#52525b"
    st.markdown(
        f"<div style='font-size:10px;color:#52525b;margin-top:.25rem;'>"
        f"<span style='color:{badge_color};font-weight:700;'>● Cache LLM:</span>"
        f" {hits} hits · {misses} chamadas reais</div>",
        unsafe_allow_html=True,
    )


# ── Filters ───────────────────────────────────────────────────────────────────


def _render_filters() -> tuple[str, str, str, str]:
    st.markdown("### 🔍 REFINAR VISÃO")
    langs, natures, types, clarities = get_filter_options(st.session_state.df)
    sel_lang: str = st.selectbox("LINGUAGEM", langs)
    sel_nature: str = st.selectbox("NATUREZA", natures)
    sel_type: str = st.selectbox("TIPO DE PROJETO", types)
    sel_clarity: str = st.selectbox("CLAREZA", clarities)
    return sel_lang, sel_nature, sel_type, sel_clarity
