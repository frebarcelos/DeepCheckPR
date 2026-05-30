from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.mappers import PRStats
from pr_analyzer.transforms.reducers import (
    EnrichedPR,
    aggregate_stats,
    count_by_contribution_nature,
    count_by_description_clarity,
    count_by_language,
    count_by_project_type,
    count_by_review_complexity,
    group_by_repo,
)


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


def test_count_by_project_type_multiple() -> None:
    prs = [
        EnrichedPR(create_sample_pr("python"), "aplicação web", "feature", "boa"),
        EnrichedPR(create_sample_pr("python"), "biblioteca", "bug fix", "excelente"),
        EnrichedPR(create_sample_pr("java"), "aplicação web", "refatoração", "boa"),
    ]
    result = count_by_project_type(prs)

    assert result == {"aplicação web": 2, "biblioteca": 1}


def test_count_by_project_type_empty() -> None:
    result = count_by_project_type([])
    assert result == {}


def test_count_by_contribution_nature_multiple() -> None:
    prs = [
        EnrichedPR(create_sample_pr("python"), "aplicação web", "feature", "boa"),
        EnrichedPR(create_sample_pr("python"), "biblioteca", "bug fix", "excelente"),
        EnrichedPR(create_sample_pr("java"), "aplicação web", "feature", "boa"),
    ]
    result = count_by_contribution_nature(prs)
    assert result == {"feature": 2, "bug fix": 1}


def test_count_by_contribution_nature_empty() -> None:
    assert count_by_contribution_nature([]) == {}


def test_count_by_description_clarity_multiple() -> None:
    prs = [
        EnrichedPR(create_sample_pr("python"), "aplicação web", "feature", "boa"),
        EnrichedPR(create_sample_pr("python"), "biblioteca", "bug fix", "excelente"),
        EnrichedPR(create_sample_pr("java"), "aplicação web", "feature", "boa"),
    ]
    result = count_by_description_clarity(prs)
    assert result == {"boa": 2, "excelente": 1}


def test_count_by_description_clarity_empty() -> None:
    assert count_by_description_clarity([]) == {}


def test_count_by_review_complexity_multiple() -> None:
    prs = [
        EnrichedPR(create_sample_pr("python"), "biblioteca", "feature", "boa", "low"),
        EnrichedPR(
            create_sample_pr("python"), "biblioteca", "bug fix", "excelente", "high"
        ),
        EnrichedPR(create_sample_pr("java"), "aplicação web", "feature", "boa", "low"),
    ]
    result = count_by_review_complexity(prs)
    assert result == {"low": 2, "high": 1}


def test_count_by_review_complexity_empty() -> None:
    assert count_by_review_complexity([]) == {}


def test_enriched_pr_default_complexity() -> None:
    pr = EnrichedPR(create_sample_pr("python"), "biblioteca", "feature", "boa")
    assert pr.review_complexity == ""


def test_enriched_pr_com_complexity() -> None:
    pr = EnrichedPR(
        create_sample_pr("python"), "biblioteca", "feature", "boa", "medium"
    )
    assert pr.review_complexity == "medium"


def test_group_by_repo_multiple() -> None:
    pr1 = create_sample_pr("python")._replace(repo_name="org/repoA")
    pr2 = create_sample_pr("java")._replace(repo_name="org/repoB")
    pr3 = create_sample_pr("go")._replace(repo_name="org/repoA")

    prs = [pr1, pr2, pr3]
    result = group_by_repo(prs)

    assert result == {
        "org/repoA": [pr1, pr3],
        "org/repoB": [pr2],
    }
    # verify immutability
    assert len(prs) == 3
    assert prs == [pr1, pr2, pr3]


def test_group_by_repo_empty() -> None:
    assert group_by_repo([]) == {}


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
