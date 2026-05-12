"""I/O layer: leitura lazy de datasets e exportação de resultados."""

from pr_analyzer.io.csv_reader import PRRecord, apply_schema, read_csv_lazy, read_prs
from pr_analyzer.io.exporters import export_to_csv, export_to_json, serialize_records

__all__ = (
    "PRRecord",
    "apply_schema",
    "export_to_csv",
    "export_to_json",
    "read_csv_lazy",
    "read_prs",
    "serialize_records",
)
