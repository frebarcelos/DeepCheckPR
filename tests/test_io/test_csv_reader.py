from pathlib import Path
from types import GeneratorType

import pytest

from pr_analyzer.io.csv_reader import PRRecord, apply_schema, read_csv_lazy, read_prs
from pr_analyzer.pipeline.builder import build_pipeline


def test_pr_record_is_immutable() -> None:
    record = PRRecord(
        pr_id=1,
        repo_name="owner/repo",
        language="python",
        title="Add parser",
        body="Implements parser",
        state="open",
        created_at="2026-05-01T10:00:00Z",
        merged_at="",
        additions=10,
        deletions=2,
        changed_files=3,
    )

    with pytest.raises(AttributeError):
        record.pr_id = 2  # type: ignore[misc]


def test_read_csv_lazy_returns_generator_and_reads_rows(tmp_path: Path) -> None:
    csv_file = tmp_path / "prs.csv"
    csv_file.write_text(
        "pr_id,repo_name,language,title\n"
        "1,owner/repo,Python,First PR\n"
        "2,owner/repo,JavaScript,Second PR\n",
        encoding="utf-8",
    )

    rows = read_csv_lazy(str(csv_file))

    assert isinstance(rows, GeneratorType)
    assert next(rows)["title"] == "First PR"
    assert next(rows)["language"] == "JavaScript"


def test_apply_schema_normalizes_missing_invalid_and_uppercase_fields() -> None:
    record = apply_schema(
        {
            "pr_id": "42",
            "repo_name": "owner/repo",
            "language": "PYTHON",
            "title": "Add cache",
            "state": "OPEN",
            "additions": "invalid",
            "deletions": "7",
        }
    )

    assert record == PRRecord(
        pr_id=42,
        repo_name="owner/repo",
        language="python",
        title="Add cache",
        body="",
        state="open",
        created_at="",
        merged_at="",
        additions=None,
        deletions=7,
        changed_files=None,
    )


def test_apply_schema_preserves_legitimate_zero_values() -> None:
    record = apply_schema(
        {
            "pr_id": "0",
            "additions": "0",
            "deletions": "0",
            "changed_files": "0",
        }
    )

    assert record.pr_id == 0
    assert record.additions == 0
    assert record.deletions == 0
    assert record.changed_files == 0


def test_read_prs_returns_generator_of_pr_records(tmp_path: Path) -> None:
    csv_file = tmp_path / "prs.csv"
    csv_file.write_text(
        "pr_id,repo_name,language,title,body,state,created_at,merged_at,additions,deletions,changed_files\n"
        "1,owner/repo,Python,First PR,Body,merged,2026-05-01T10:00:00Z,2026-05-02T10:00:00Z,5,1,2\n",
        encoding="utf-8",
    )

    records = read_prs(str(csv_file))

    assert isinstance(records, GeneratorType)
    assert next(records) == PRRecord(
        pr_id=1,
        repo_name="owner/repo",
        language="python",
        title="First PR",
        body="Body",
        state="merged",
        created_at="2026-05-01T10:00:00Z",
        merged_at="2026-05-02T10:00:00Z",
        additions=5,
        deletions=1,
        changed_files=2,
    )


def test_read_prs_integrates_with_build_pipeline_lazily(tmp_path: Path) -> None:
    csv_file = tmp_path / "prs.csv"
    csv_file.write_text(
        "pr_id,repo_name,language,title,body,state,created_at,merged_at,additions,deletions,changed_files\n"
        "1,owner/repo,Python,First PR,Body,open,2026-05-01T10:00:00Z,,5,1,2\n"
        "2,owner/repo,Go,Second PR,Body,closed,2026-05-02T10:00:00Z,,3,2,1\n",
        encoding="utf-8",
    )

    pipeline = build_pipeline(
        read_prs(str(csv_file)),
        filters=(lambda pr: pr.state == "open",),
        mappers=(lambda pr: pr,),
    )

    assert not isinstance(pipeline, list | tuple)
    assert list(pipeline) == [
        PRRecord(
            pr_id=1,
            repo_name="owner/repo",
            language="python",
            title="First PR",
            body="Body",
            state="open",
            created_at="2026-05-01T10:00:00Z",
            merged_at="",
            additions=5,
            deletions=1,
            changed_files=2,
        )
    ]
