#!/usr/bin/env python3
"""Demonstração da fase 2 do dev1: leitura lazy, pipeline e exportação."""

import tempfile
from pathlib import Path

from pr_analyzer.io import export_to_csv, export_to_json, read_prs
from pr_analyzer.pipeline.builder import build_pipeline

SAMPLE_CSV = """pr_id,repo_name,language,title,body,state,created_at,merged_at,additions,deletions,changed_files
1,owner/repo,Python,Adicionar exportador CSV,Implementa exportador,open,2026-05-10T10:00:00Z,,12,3,2
2,owner/repo,Go,Fechar PR obsoleto,Nao e mais necessario,closed,2026-05-10T11:00:00Z,,0,0,1
3,owner/repo,Python,Corrigir inteiro invalido,Mantem campos invalidos como None,open,2026-05-10T12:00:00Z,,invalid,4,1
"""


def main() -> None:
    """Executa um fluxo ponta a ponta sem depender do dataset real."""
    workspace = Path(tempfile.mkdtemp(prefix="pr-analyzer-io-demo-"))
    source = workspace / "sample_prs.csv"
    csv_output = workspace / "open_prs.csv"
    json_output = workspace / "open_prs.json"

    source.write_text(SAMPLE_CSV, encoding="utf-8")

    open_prs = build_pipeline(
        read_prs(str(source)),
        filters=(lambda pr: pr.state == "open",),
    )
    records = tuple(open_prs)

    export_to_csv(records, csv_output)
    export_to_json(records, json_output)

    print(f"PRs abertos exportados: {len(records)}")
    print(f"CSV: {csv_output}")
    print(f"JSON: {json_output}")
    print(json_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
