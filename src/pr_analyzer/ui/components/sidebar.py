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


def render_sidebar() -> tuple[str, str, bool, bool, bool]:
    """
    Render the full sidebar and return:
        (sel_lang, sel_nature, cleaning, llm_tag, metrics)
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
            st.rerun()
    else:
        st.markdown(
            "<p style='font-size:10px;color:#52525b;font-weight:700;"
            "text-align:center;margin:.5rem 0;'>NENHUM DATASET ATIVO</p>",
            unsafe_allow_html=True,
        )


def _handle_upload(uploaded: object) -> None:
    """Route uploaded CSVs through the functional pipeline when possible.

    The Streamlit UploadedFile cursor may be at an arbitrary position after
    widget rendering, so we always seek(0) and read into a fresh BytesIO
    before passing to any parser — avoiding empty-read errors.
    """
    from io import BytesIO

    filename = getattr(uploaded, "name", "uploaded.csv")
    try:
        if hasattr(uploaded, "seek"):
            uploaded.seek(0)
        raw_bytes: bytes = uploaded.read() if hasattr(uploaded, "read") else b""
        buf = BytesIO(raw_bytes)
        if filename.endswith(".csv"):
            df, prs = load_uploaded(buf, filename)
            st.session_state.df = df
            st.session_state.raw_prs = prs
        else:
            st.session_state.df = load_dataframe(buf, filename)
            st.session_state.raw_prs = None
        st.session_state.file_loaded = True
        st.session_state.fname = filename
        st.session_state.llm_cache_stats = None
    except Exception as exc:
        st.error(f"Não foi possível carregar \"{filename}\": {exc}")


def _render_local_datasets() -> None:
    datasets = discover_datasets("data")
    if not datasets:
        return

    with st.expander("DATASETS LOCAIS", expanded=True):
        labels: list[str] = ["— selecionar —", *(d["label"] for d in datasets)]
        choice: str = st.selectbox(
            "Dataset local",
            labels,
            key="local_ds_select",
            label_visibility="collapsed",
        )
        if choice != "— selecionar —":
            selected = next(d for d in datasets if d["label"] == choice)
            if selected.get("oversized"):
                st.warning(
                    f"Arquivo excede o limite configurado "
                    f"({os.environ.get('MAX_DATASET_SIZE_GB', '10')} GB). "
                    "Ajuste MAX_DATASET_SIZE_GB no .env para carregar."
                )
            elif st.button(
                "Carregar", key="load_local_btn", use_container_width=True
            ):
                _load_local(selected)


def _load_local(dataset: dict[str, Any]) -> None:
    fmt: str = dataset["format"]
    path: str = dataset["path"]

    if fmt == "archive":
        lang = str(dataset.get("lang", ""))
        with st.spinner(f"Amostrando {lang} (2 000 registros)…"):
            df = load_archive_sample(path, lang)
    elif fmt == "csv":
        df = pd.read_csv(path)
    else:
        with open(path, encoding="utf-8") as jf:
            df = pd.DataFrame(json.load(jf))

    st.session_state.df = df
    st.session_state.file_loaded = True
    st.session_state.fname = dataset["label"]
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


def _render_filters() -> tuple[str, str]:
    st.markdown("### 🔍 REFINAR VISÃO")
    langs, natures = get_filter_options(st.session_state.df)
    sel_lang: str = st.selectbox("LINGUAGEM", langs)
    sel_nature: str = st.selectbox("NATUREZA", natures)
    return sel_lang, sel_nature
