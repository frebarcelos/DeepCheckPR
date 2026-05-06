from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.mappers import PRStats, compute_stats


def create_sample_pr(
    body: str = "", additions: int = 0, deletions: int = 0, merged_at: str = ""
) -> PRRecord:
    return PRRecord(
        pr_id=1,
        repo_name="test/repo",
        language="python",
        title="Test PR",
        body=body,
        state="open",
        created_at="2023-05-15T09:00:00Z",
        merged_at=merged_at,
        additions=additions,
        deletions=deletions,
        changed_files=1,
    )


def test_compute_stats_normal_pr() -> None:
    pr = create_sample_pr(
        body="This is a test PR with 8 words.",
        additions=10,
        deletions=5,
        merged_at="2023-05-15T10:00:00Z",
    )
    stats = compute_stats(pr)

    assert isinstance(stats, PRStats)
    assert stats.body_char_count == 31
    assert stats.body_word_count == 8
    assert stats.total_changes == 15
    assert stats.is_merged is True


def test_compute_stats_empty_body() -> None:
    pr = create_sample_pr(body="")
    stats = compute_stats(pr)
    assert stats.body_char_count == 0
    assert stats.body_word_count == 0


def test_compute_stats_not_merged() -> None:
    pr = create_sample_pr(merged_at="")
    stats = compute_stats(pr)
    assert stats.is_merged is False


def test_compute_stats_zero_changes() -> None:
    pr = create_sample_pr(additions=0, deletions=0)
    stats = compute_stats(pr)
    assert stats.total_changes == 0
