#!/usr/bin/env python3
"""CLI para processar dataset completo via pipeline LLM otimizado.

Suporta dois formatos de entrada:
  - CSV  com colunas PRRecord (pr_id, repo_name, language, title, body, ...)
  - JSON mined-comments (formato {repo: [{id, path, body, ...}, ...]})

Uso:
    python scripts/run_pipeline.py <dataset> <output.json> [limit]

    limit=0 (padrão) → processa TODOS os registros do arquivo
    limit=N          → processa os primeiros N registros

Exemplos:
    # Processa tudo com auto-detecção de hardware
    LLM_MAX_WORKERS=auto LLM_USE_TOOLS=true LLM_BATCH_SIZE=5 \\
        python scripts/run_pipeline.py data/Python.json out.json

    # Processa amostra de 500 com Ollama
    LLM_BACKEND=ollama LLM_MODEL=qwen2:1.5b \\
        python scripts/run_pipeline.py data/Python.json out.json 500

Variáveis de ambiente relevantes:
    LLM_BACKEND          groq (padrão) | ollama
    LLM_MODEL            modelo (llama3-8b-8192 para Groq / qwen2:1.5b para Ollama)
    LLM_MAX_WORKERS      número de threads paralelas | auto (detecta hardware)
    LLM_USE_TOOLS        true | false — tool calling (1 chamada/PR em vez de 3)
    LLM_BATCH_SIZE       PRs por chamada batch (requer LLM_USE_TOOLS=true)
    LLM_MAX_RETRIES      tentativas de retry em falha (padrão: 3)
"""

import json
import sys
from collections.abc import Generator
from pathlib import Path

import ijson
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pr_analyzer.io.csv_reader import PRRecord, read_prs  # noqa: E402
from pr_analyzer.llm.classifiers import enrich_prs  # noqa: E402
from pr_analyzer.llm.client import create_llm_client  # noqa: E402
from pr_analyzer.llm.metrics import ClassificationMetrics  # noqa: E402
from pr_analyzer.llm.system_probe import load_pipeline_config  # noqa: E402


def _language_from_path(filepath: str) -> str:
    name = Path(filepath).stem.lower()
    for lang in ("python", "java", "javascript", "typescript", "go"):
        if lang in name:
            return lang
    return "unknown"


def read_mined_comments(filepath: str, limit: int) -> Generator[PRRecord, None, None]:
    """Lê mined-comments via streaming (ijson). limit=0 → sem limite."""
    language = _language_from_path(filepath)
    count = 0
    with open(filepath, "rb") as f:
        for repo_name, comment in ijson.kvitems(f, ""):
            for c in comment:
                if limit > 0 and count >= limit:
                    return
                body = str(c.get("body") or "").strip()
                title = str(c.get("path") or repo_name).strip()
                yield PRRecord(
                    pr_id=int(c.get("id", 0)) or None,
                    repo_name=repo_name,
                    language=language,
                    title=title,
                    body=body,
                    state="merged",
                    created_at="",
                    merged_at="",
                    additions=None,
                    deletions=None,
                    changed_files=None,
                )
                count += 1


def load_prs(filepath: str, limit: int) -> list[PRRecord]:
    """Carrega PRRecords do arquivo. limit=0 → todos os registros."""
    if filepath.endswith(".json"):
        desc = f"lendo {limit} registros" if limit > 0 else "lendo TUDO (sem limite)"
        print(f"  Formato: mined-comments JSON (streaming, {desc})...")
        return list(read_mined_comments(filepath, limit))
    desc = f"primeiros {limit}" if limit > 0 else "todos"
    print(f"  Formato: CSV PRRecord ({desc} registros)...")
    prs = list(read_prs(filepath))
    return prs[:limit] if limit > 0 else prs


def main(dataset_path: str, output_path: str, limit: int = 0) -> None:
    print(f"\nCarregando '{dataset_path}'...")
    prs = load_prs(dataset_path, limit)
    print(f"  {len(prs)} registros carregados.")

    cfg = load_pipeline_config()
    max_workers = int(cfg["max_workers"])
    use_tools = bool(cfg["use_tools"])
    batch_size = int(cfg["batch_size"])
    print(
        f"  Config: workers={max_workers} | use_tools={use_tools} | batch_size={batch_size}"
    )

    client = create_llm_client()
    metrics = ClassificationMetrics()

    print("Classificando (LLM — pode demorar na primeira vez)...")
    results = list(
        enrich_prs(
            prs,
            client,
            cache_path=Path(".cache/pipeline.json"),
            max_workers=max_workers,
            use_tools=use_tools,
            batch_size=batch_size,
            metrics=metrics,
        )
    )

    print(f"\n  Throughput : {metrics.throughput_prs_per_min:.1f} PRs/min")
    print(f"  Total time : {metrics.total_time_s:.1f}s")
    if metrics.batch_calls:
        print(
            f"  Fallback   : {metrics.fallback_rate:.1%} ({metrics.batch_fallbacks}/{metrics.batch_calls} batches)"
        )
    for field, counts in metrics.value_counts.items():
        top = sorted(counts.items(), key=lambda x: -x[1])[:3]
        print(f"  {field}: {dict(top)}")

    output = [
        {
            "pr_id": r.pr.pr_id,
            "repo": r.pr.repo_name,
            "language": r.pr.language,
            "title": r.pr.title,
            "project_type": r.project_type,
            "contribution_nature": r.contribution_nature,
            "description_clarity": r.description_clarity,
        }
        for r in results
    ]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✓ {len(output)} registros → '{output_path}'")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/run_pipeline.py <dataset> <output.json> [limit=0]")
        print("     limit=0 processa TODOS os registros")
        sys.exit(1)

    _limit = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    main(sys.argv[1], sys.argv[2], _limit)
