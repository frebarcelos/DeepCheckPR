from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.mappers import PRStats
from pr_analyzer.transforms.reducers import aggregate_stats, count_by_language


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


def test_aggregate_stats_multiple() -> None:
    stats = [
        PRStats(
            body_char_count=100, body_word_count=20, total_changes=10, is_merged=True
        ),
        PRStats(
            body_char_count=200, body_word_count=40, total_changes=30, is_merged=False
        ),
    ]
    result = aggregate_stats(stats)

    assert result["avg_chars"] == 150.0
    assert result["avg_words"] == 30.0
    assert result["avg_changes"] == 20.0
    assert result["merge_rate"] == 0.5


def test_aggregate_stats_empty() -> None:
    result = aggregate_stats([])
    assert result == {
        "avg_chars": 0.0,
        "avg_words": 0.0,
        "avg_changes": 0.0,
        "merge_rate": 0.0,
    }


def test_aggregate_stats_single() -> None:
    stats = [
        PRStats(body_char_count=10, body_word_count=2, total_changes=5, is_merged=True),
    ]
    result = aggregate_stats(stats)
    assert result == {
        "avg_chars": 10.0,
        "avg_words": 2.0,
        "avg_changes": 5.0,
        "merge_rate": 1.0,
    }
