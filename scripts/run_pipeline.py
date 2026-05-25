#!/usr/bin/env python3
"""CLI para testar o pipeline completo (dataset → LLM → JSON) sem depender da UI.

Suporta dois formatos de entrada:
  - CSV  com colunas PRRecord (pr_id, repo_name, language, title, body, ...)
  - JSON mined-comments (formato {repo: [{id, path, body, ...}, ...]})

Uso:
    python scripts/run_pipeline.py <dataset> <output.json> [limit]

Exemplos:
    LLM_BACKEND=ollama python scripts/run_pipeline.py data/archive/.../Python.json out.json 5
    LLM_BACKEND=ollama LLM_MODEL=mistral python scripts/run_pipeline.py data.csv out.json 20

Variáveis de ambiente:
    LLM_BACKEND   groq (padrão) | ollama
    LLM_MODEL     modelo (padrão: llama3-8b-8192 para Groq / llama3 para Ollama)
"""

import json
import sys
from collections.abc import Generator
from pathlib import Path

import ijson
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pr_analyzer.cache.memo import make_enriched_classifier  # noqa: E402
from pr_analyzer.io.csv_reader import PRRecord, read_prs  # noqa: E402
from pr_analyzer.llm.classifiers import (  # noqa: E402
    avaliar_clareza_descricao,
    classificar_natureza_contribuicao,
    classificar_tipo_projeto,
)
from pr_analyzer.llm.client import create_llm_client  # noqa: E402
from pr_analyzer.pipeline.builder import enrich_pipeline  # noqa: E402


def _language_from_path(filepath: str) -> str:
    name = Path(filepath).stem.lower()
    for lang in ("python", "java", "javascript", "typescript", "go"):
        if lang in name:
            return lang
    return "unknown"


def read_mined_comments(filepath: str, limit: int) -> Generator[PRRecord, None, None]:
    """Lê o formato mined-comments via streaming (ijson) — não carrega o arquivo inteiro."""
    language = _language_from_path(filepath)
    count = 0
    with open(filepath, "rb") as f:
        # itera sobre cada item de cada array: "repo_name.item"
        for repo_name, comment in ijson.kvitems(f, ""):
            for c in comment:
                if count >= limit:
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
    if filepath.endswith(".json"):
        print(f"  Formato: mined-comments JSON (streaming, lendo {limit} registros...)")
        return list(read_mined_comments(filepath, limit))
    print(f"  Formato: CSV PRRecord (lendo {limit} registros...)")
    return list(read_prs(filepath))[:limit]


def main(dataset_path: str, output_path: str, limit: int = 10) -> None:
    print(f"Carregando dados de '{dataset_path}'...")
    prs = load_prs(dataset_path, limit)
    print(f"  {len(prs)} registros carregados.")

    print("Criando cliente LLM...")
    client = create_llm_client()

    classify_fn = make_enriched_classifier(
        lambda repo, title: classificar_tipo_projeto(repo, [title], client),
        lambda title, body: classificar_natureza_contribuicao(title, body, client),
        lambda body: avaliar_clareza_descricao(body, client),
        cache_path=Path(".cache/pipeline.json"),
    )

    print("Classificando (pode demorar na primeira vez)...")
    results = list(enrich_pipeline(prs, classify_fn))

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
    print(f"✓ {len(output)} registros processados → '{output_path}'")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/run_pipeline.py <dataset> <output.json> [limit=10]")
        sys.exit(1)

    _limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    main(sys.argv[1], sys.argv[2], _limit)
