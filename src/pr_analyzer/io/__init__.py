"""I/O layer: leitura lazy de datasets e exportação de resultados."""

from pr_analyzer.io.csv_reader import (
    PRRecord,
    apply_schema,
    detect_schema,
    is_valid_row,
    read_csv_lazy,
    read_prs,
    schema_adapter,
)
from pr_analyzer.io.exporters import export_to_csv, export_to_json, serialize_records

__all__ = (
    "PRRecord",
    "apply_schema",
    "detect_schema",
    "export_to_csv",
    "export_to_json",
    "is_valid_row",
    "read_csv_lazy",
    "read_prs",
    "schema_adapter",
    "serialize_records",
)
