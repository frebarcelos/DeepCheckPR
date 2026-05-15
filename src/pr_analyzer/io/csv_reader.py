"""Leitores CSV e normalizacao de schema para Pull Requests do GitHub."""

import csv
from collections.abc import Callable, Generator, Iterable, Mapping
from os import PathLike
from typing import NamedTuple

FilePath = str | PathLike[str]

CAMPOS_CANONICOS = (
    "pr_id",
    "repo_name",
    "language",
    "title",
    "body",
    "state",
    "created_at",
    "merged_at",
    "additions",
    "deletions",
    "changed_files",
)

MAPEAMENTO_CANONICO = tuple((campo, campo) for campo in CAMPOS_CANONICOS)
MAPEAMENTO_GITHUB_EXPORT = (
    ("pr_id", "number"),
    ("repo_name", "repository"),
    ("language", "primary_language"),
    ("title", "title"),
    ("body", "description"),
    ("state", "status"),
    ("created_at", "created"),
    ("merged_at", "merged"),
    ("additions", "additions"),
    ("deletions", "deletions"),
    ("changed_files", "files_changed"),
)
SCHEMAS_CONHECIDOS = (
    ("canonical", MAPEAMENTO_CANONICO),
    ("github_export", MAPEAMENTO_GITHUB_EXPORT),
)


class PRRecord(NamedTuple):
    """Registro imutavel de Pull Request normalizado a partir do CSV."""

    pr_id: int | None
    repo_name: str
    language: str
    title: str
    body: str
    state: str
    created_at: str
    merged_at: str
    additions: int | None
    deletions: int | None
    changed_files: int | None


def _text(raw_row: Mapping[str, object], field: str) -> str:
    value = raw_row.get(field, "")
    return "" if value is None else str(value).strip()


def _is_integer_text(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and stripped.lstrip("+-").isdigit()


def _integer(raw_row: Mapping[str, object], field: str) -> int | None:
    value = _text(raw_row, field)
    return int(value) if _is_integer_text(value) else None


def _normalized_header(header: Iterable[str | None]) -> frozenset[str]:
    return frozenset(str(field).strip().lower() for field in header if field)


def _schema_fields(mapping: tuple[tuple[str, str], ...]) -> frozenset[str]:
    return frozenset(source for _, source in mapping)


def detect_schema(header: Iterable[str | None]) -> str:
    """Identifica o schema do CSV a partir do cabecalho."""
    fields = _normalized_header(header)
    matched = tuple(
        schema_name
        for schema_name, mapping in SCHEMAS_CONHECIDOS
        if _schema_fields(mapping).issubset(fields)
    )
    return matched[0] if matched else "unknown"


def _mapping_for_schema(schema_name: str) -> tuple[tuple[str, str], ...]:
    matched = tuple(
        mapping
        for known_name, mapping in SCHEMAS_CONHECIDOS
        if known_name == schema_name
    )
    if matched:
        return matched[0]
    msg = f"schema desconhecido: {schema_name}"
    raise ValueError(msg)


def schema_adapter(
    schema_name: str,
) -> Callable[[Mapping[str, object]], dict[str, object]]:
    """Retorna uma funcao que converte uma linha para os campos canonicos."""
    mapping = _mapping_for_schema(schema_name)
    return lambda row: {target: row.get(source, "") for target, source in mapping}


def read_csv_lazy(
    filepath: FilePath,
    encoding: str = "utf-8",
) -> Generator[dict[str, str], None, None]:
    """Produz linhas brutas do CSV sem carregar o arquivo inteiro em memoria."""
    with open(filepath, encoding=encoding, newline="") as csv_file:
        yield from csv.DictReader(csv_file)


def apply_schema(raw_row: Mapping[str, object]) -> PRRecord:
    """Converte uma linha canonica em um PRRecord imutavel e tipado."""
    return PRRecord(
        pr_id=_integer(raw_row, "pr_id"),
        repo_name=_text(raw_row, "repo_name"),
        language=_text(raw_row, "language").lower(),
        title=_text(raw_row, "title"),
        body=_text(raw_row, "body"),
        state=_text(raw_row, "state").lower(),
        created_at=_text(raw_row, "created_at"),
        merged_at=_text(raw_row, "merged_at"),
        additions=_integer(raw_row, "additions"),
        deletions=_integer(raw_row, "deletions"),
        changed_files=_integer(raw_row, "changed_files"),
    )


def _read_adapted_rows(
    filepath: FilePath,
    encoding: str,
) -> Generator[dict[str, object], None, None]:
    with open(filepath, encoding=encoding, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        adapter = schema_adapter(detect_schema(reader.fieldnames or ()))
        yield from map(adapter, reader)


def read_prs(
    filepath: FilePath,
    encoding: str = "utf-8",
) -> Generator[PRRecord, None, None]:
    """Produz PRRecords normalizados a partir de um CSV."""
    return (apply_schema(row) for row in _read_adapted_rows(filepath, encoding))
