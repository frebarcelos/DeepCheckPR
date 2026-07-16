"""Shared fixtures for the pr-analyzer test suite."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pr_analyzer.io.csv_reader import PRRecord


@pytest.fixture
def sample_pr() -> PRRecord:
    return PRRecord(
        pr_id=1,
        repo_name="org/repo",
        language="python",
        title="Fix memory leak in parser",
        body="This PR fixes a memory leak found in the CSV parser module.",
        state="merged",
        created_at="2024-01-01T10:00:00Z",
        merged_at="2024-01-02T12:00:00Z",
        additions=42,
        deletions=7,
        changed_files=3,
    )


@pytest.fixture
def sample_pr_no_body(sample_pr: PRRecord) -> PRRecord:
    return sample_pr._replace(body="")


@pytest.fixture
def sample_prs(sample_pr: PRRecord) -> tuple[PRRecord, ...]:
    return (
        sample_pr,
        sample_pr._replace(pr_id=2, language="java", state="open", merged_at=""),
        sample_pr._replace(pr_id=3, language="python", state="closed", merged_at=""),
    )


@pytest.fixture
def sample_csv_file(tmp_path: Path, sample_pr: PRRecord) -> str:
    csv_path = tmp_path / "prs.csv"
    csv_path.write_text(
        "pr_id,repo_name,language,title,body,state,created_at,merged_at,"
        "additions,deletions,changed_files\n"
        f"{sample_pr.pr_id},{sample_pr.repo_name},{sample_pr.language},"
        f'"{sample_pr.title}","{sample_pr.body}",{sample_pr.state},'
        f"{sample_pr.created_at},{sample_pr.merged_at},"
        f"{sample_pr.additions},{sample_pr.deletions},{sample_pr.changed_files}\n",
        encoding="utf-8",
    )
    return str(csv_path)


@pytest.fixture
def mock_llm_client() -> MagicMock:
    client = MagicMock()
    client.run.return_value.content = '{"tipo_projeto": "biblioteca"}'
    return client
