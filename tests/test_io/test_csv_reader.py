from pathlib import Path
from types import GeneratorType

import pytest

from pr_analyzer.io.csv_reader import (
    PRRecord,
    apply_schema,
    detect_schema,
    is_valid_row,
    read_csv_lazy,
    read_prs,
    schema_adapter,
)
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


def test_detect_schema_identifies_canonical_header() -> None:
    header = (
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

    assert detect_schema(header) == "canonical"


def test_detect_schema_identifies_github_export_header() -> None:
    header = (
        "number",
        "repository",
        "primary_language",
        "title",
        "description",
        "status",
        "created",
        "merged",
        "additions",
        "deletions",
        "files_changed",
    )

    assert detect_schema(header) == "github_export"


def test_schema_adapter_normalizes_github_export_row() -> None:
    adapter = schema_adapter("github_export")

    assert adapter(
        {
            "number": "7",
            "repository": "owner/repo",
            "primary_language": "Python",
            "title": "Nova tela",
            "description": "Implementa a tela inicial",
            "status": "OPEN",
            "created": "2026-05-10T12:00:00Z",
            "merged": "",
            "additions": "12",
            "deletions": "3",
            "files_changed": "2",
        }
    ) == {
        "pr_id": "7",
        "repo_name": "owner/repo",
        "language": "Python",
        "title": "Nova tela",
        "body": "Implementa a tela inicial",
        "state": "OPEN",
        "created_at": "2026-05-10T12:00:00Z",
        "merged_at": "",
        "additions": "12",
        "deletions": "3",
        "changed_files": "2",
    }


def test_schema_adapter_rejects_unknown_schema() -> None:
    with pytest.raises(ValueError, match="schema desconhecido"):
        schema_adapter("inexistente")


def test_is_valid_row_rejects_missing_required_field() -> None:
    assert not is_valid_row(
        {
            "pr_id": "1",
            "repo_name": "",
            "language": "Python",
            "title": "Sem repo",
            "state": "open",
            "additions": "1",
            "deletions": "0",
            "changed_files": "1",
        }
    )


def test_is_valid_row_rejects_invalid_integer_field() -> None:
    assert not is_valid_row(
        {
            "pr_id": "abc",
            "repo_name": "owner/repo",
            "language": "Python",
            "title": "Inteiro invalido",
            "state": "open",
            "additions": "1",
            "deletions": "0",
            "changed_files": "1",
        }
    )


def test_read_prs_filters_malformed_rows(tmp_path: Path) -> None:
    csv_file = tmp_path / "prs.csv"
    csv_file.write_text(
        "pr_id,repo_name,language,title,body,state,created_at,merged_at,additions,deletions,changed_files\n"
        "1,owner/repo,Python,Valido,Body,open,2026-05-01T10:00:00Z,,5,1,2\n"
        "abc,owner/repo,Python,Invalido,Body,open,2026-05-01T10:00:00Z,,5,1,2\n"
        "3,,Python,Sem repo,Body,open,2026-05-01T10:00:00Z,,5,1,2\n",
        encoding="utf-8",
    )

    assert list(read_prs(str(csv_file))) == [
        PRRecord(
            pr_id=1,
            repo_name="owner/repo",
            language="python",
            title="Valido",
            body="Body",
            state="open",
            created_at="2026-05-01T10:00:00Z",
            merged_at="",
            additions=5,
            deletions=1,
            changed_files=2,
        )
    ]


def test_read_prs_returns_empty_for_empty_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "vazio.csv"
    csv_file.write_text("", encoding="utf-8")

    assert list(read_prs(csv_file)) == []


def test_read_prs_returns_empty_for_header_only_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "apenas_cabecalho.csv"
    csv_file.write_text(
        "pr_id,repo_name,language,title,body,state,created_at,merged_at,additions,deletions,changed_files\n",
        encoding="utf-8",
    )

    assert list(read_prs(csv_file)) == []


def test_read_prs_ignores_unexpected_extra_fields(tmp_path: Path) -> None:
    csv_file = tmp_path / "campos_extras.csv"
    csv_file.write_text(
        "pr_id,repo_name,language,title,body,state,created_at,merged_at,additions,deletions,changed_files,reviewers,labels\n"
        "9,owner/repo,Python,Com extras,Body,open,2026-05-04T10:00:00Z,,6,2,1,ana;bia,backend\n",
        encoding="utf-8",
    )

    assert list(read_prs(csv_file)) == [
        PRRecord(
            pr_id=9,
            repo_name="owner/repo",
            language="python",
            title="Com extras",
            body="Body",
            state="open",
            created_at="2026-05-04T10:00:00Z",
            merged_at="",
            additions=6,
            deletions=2,
            changed_files=1,
        )
    ]


def test_read_prs_supports_latin_1_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "prs_latin1.csv"
    csv_file.write_text(
        "number,repository,primary_language,title,description,status,created,merged,additions,deletions,files_changed\n"
        "8,owner/repo,Python,Correção,Descrição com acento,open,2026-05-03T10:00:00Z,,4,1,1\n",
        encoding="latin-1",
    )

    assert next(read_prs(str(csv_file), encoding="latin-1")) == PRRecord(
        pr_id=8,
        repo_name="owner/repo",
        language="python",
        title="Correção",
        body="Descrição com acento",
        state="open",
        created_at="2026-05-03T10:00:00Z",
        merged_at="",
        additions=4,
        deletions=1,
        changed_files=1,
    )


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
