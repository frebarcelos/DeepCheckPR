"""I/O layer: leitura lazy de datasets e exportação de resultados."""

from pr_analyzer.io.csv_reader import PRRecord, apply_schema, read_csv_lazy, read_prs

__all__ = ("PRRecord", "apply_schema", "read_csv_lazy", "read_prs")
