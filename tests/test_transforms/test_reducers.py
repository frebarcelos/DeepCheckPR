from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.reducers import count_by_language


def create_sample_pr(language: str) -> PRRecord:
    return PRRecord(
        pr_id=1,
        repo_name="test/repo",
        language=language,
        title="Test PR",
        body="",
        state="open",
        created_at="2023-05-15T09:00:00Z",
        merged_at="",
        additions=0,
        deletions=0,
        changed_files=1,
    )


def test_count_by_language_multiple() -> None:
    prs = [
        create_sample_pr("python"),
        create_sample_pr("python"),
        create_sample_pr("java"),
        create_sample_pr("unknown"),
    ]
    result = count_by_language(prs)

    assert result == {"python": 2, "java": 1, "unknown": 1}


def test_count_by_language_empty() -> None:
    result = count_by_language([])
    assert result == {}


def test_count_by_language_unknown_only() -> None:
    prs = [create_sample_pr("unknown")]
    result = count_by_language(prs)
    assert result == {"unknown": 1}
