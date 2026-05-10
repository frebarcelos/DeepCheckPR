import csv
import json
from pathlib import Path

import pytest

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.io.exporters import export_to_csv, export_to_json, serialize_records


def _record() -> PRRecord:
    return PRRecord(
        pr_id=1,
        repo_name="owner/repo",
        language="python",
        title="Add exporter",
        body="Implements CSV and JSON export",
        state="open",
        created_at="2026-05-10T10:00:00Z",
        merged_at="",
        additions=12,
        deletions=3,
        changed_files=2,
    )


def test_serialize_records_converts_named_tuple_to_dict() -> None:
    assert serialize_records([_record()]) == [
        {
            "pr_id": 1,
            "repo_name": "owner/repo",
            "language": "python",
            "title": "Add exporter",
            "body": "Implements CSV and JSON export",
            "state": "open",
            "created_at": "2026-05-10T10:00:00Z",
            "merged_at": "",
            "additions": 12,
            "deletions": 3,
            "changed_files": 2,
        }
    ]


def test_serialize_records_copies_dict_records() -> None:
    original = {"repo_name": "owner/repo", "state": "open"}

    result = serialize_records([original])

    assert result == [{"repo_name": "owner/repo", "state": "open"}]
    assert result[0] is not original


def test_export_to_csv_writes_serialized_records(tmp_path: Path) -> None:
    csv_file = tmp_path / "prs.csv"

    export_to_csv([_record()], csv_file)

    with csv_file.open(encoding="utf-8", newline="") as output:
        rows = list(csv.DictReader(output))

    assert rows == [
        {
            "pr_id": "1",
            "repo_name": "owner/repo",
            "language": "python",
            "title": "Add exporter",
            "body": "Implements CSV and JSON export",
            "state": "open",
            "created_at": "2026-05-10T10:00:00Z",
            "merged_at": "",
            "additions": "12",
            "deletions": "3",
            "changed_files": "2",
        }
    ]


def test_export_to_csv_writes_empty_file_for_empty_records(tmp_path: Path) -> None:
    csv_file = tmp_path / "empty.csv"

    export_to_csv([], csv_file)

    assert csv_file.read_text(encoding="utf-8") == ""


def test_export_to_json_writes_serialized_records(tmp_path: Path) -> None:
    json_file = tmp_path / "prs.json"

    export_to_json([_record()], json_file)

    assert json.loads(json_file.read_text(encoding="utf-8")) == serialize_records(
        [_record()]
    )


def test_serialize_records_rejects_unknown_record_type() -> None:
    with pytest.raises(TypeError, match="Mapping ou objeto compatível com NamedTuple"):
        serialize_records([object()])
