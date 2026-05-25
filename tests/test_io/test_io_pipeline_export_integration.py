import csv
import json
from pathlib import Path

from pr_analyzer.io.csv_reader import read_prs
from pr_analyzer.io.exporters import export_to_csv, export_to_json
from pr_analyzer.pipeline.builder import build_pipeline
from pr_analyzer.transforms.filters import by_state
from pr_analyzer.transforms.mappers import compute_stats


def test_read_pipeline_and_export_end_to_end(tmp_path: Path) -> None:
    csv_entrada = tmp_path / "prs.csv"
    csv_saida = tmp_path / "resultado.csv"
    json_saida = tmp_path / "resultado.json"
    csv_entrada.write_text(
        "pr_id,repo_name,language,title,body,state,created_at,merged_at,additions,deletions,changed_files\n"
        "1,owner/repo,Python,Aberto,Texto da descricao,open,2026-05-20T10:00:00Z,,10,4,2\n"
        "2,owner/repo,Python,Fechado,Outro texto,closed,2026-05-21T10:00:00Z,,5,1,1\n",
        encoding="utf-8",
    )

    resultado = tuple(
        build_pipeline(
            read_prs(csv_entrada),
            filters=(by_state("open"),),
            mappers=(compute_stats,),
        )
    )

    export_to_csv(resultado, csv_saida)
    export_to_json(resultado, json_saida)

    with csv_saida.open(encoding="utf-8", newline="") as arquivo_csv:
        linhas_csv = list(csv.DictReader(arquivo_csv))

    assert linhas_csv == [
        {
            "body_char_count": "18",
            "body_word_count": "3",
            "total_changes": "14",
            "is_merged": "False",
        }
    ]
    assert json.loads(json_saida.read_text(encoding="utf-8")) == [
        {
            "body_char_count": 18,
            "body_word_count": 3,
            "total_changes": 14,
            "is_merged": False,
        }
    ]
