"""Exportadores de registros de Pull Requests para arquivos serializados."""

import csv
import json
from collections.abc import Iterable, Mapping
from itertools import chain
from os import PathLike
from typing import Any

FilePath = str | PathLike[str]


def _serialize_record(record: Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        return dict(record)
    if hasattr(record, "_asdict"):
        return dict(record._asdict())
    msg = "registro deve ser Mapping ou objeto compatível com NamedTuple"
    raise TypeError(msg)


def serialize_records(records: Iterable[Any]) -> list[dict[str, Any]]:
    """Converte mappings ou NamedTuples em dicionários serializáveis."""
    return list(map(_serialize_record, records))


def _fieldnames(records: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(chain.from_iterable(record.keys() for record in records))
    )


def export_to_csv(records: Iterable[Any], filepath: FilePath) -> None:
    """Escreve registros em CSV após serializá-los como dicionários."""
    serialized = serialize_records(records)

    with open(filepath, "w", encoding="utf-8", newline="") as csv_file:
        fields = _fieldnames(serialized)
        if not fields:
            return
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(serialized)


def export_to_json(records: Iterable[Any], filepath: FilePath) -> None:
    """Escreve registros em JSON após serializá-los como dicionários."""
    serialized = serialize_records(records)

    with open(filepath, "w", encoding="utf-8") as json_file:
        json.dump(serialized, json_file, ensure_ascii=False, indent=2)
