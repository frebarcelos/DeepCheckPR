from pathlib import Path
from unittest.mock import MagicMock

from pr_analyzer.cache.memo import cached_classify, make_enriched_classifier
from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.pipeline.builder import EnrichedPR


def _make_pr() -> PRRecord:
    return PRRecord(
        pr_id=1,
        repo_name="org/repo",
        language="python",
        title="Fix bug",
        body="Detailed body.",
        state="merged",
        created_at="2024-01-01",
        merged_at="2024-01-02",
        additions=5,
        deletions=2,
        changed_files=1,
    )


def _make_classifier(return_value: str = "tool") -> MagicMock:
    fn = MagicMock(return_value=return_value)
    fn.__name__ = "mock_classifier"
    return fn


def test_cached_classify_returns_correct_result() -> None:
    classifier = _make_classifier("tool")
    wrapped = cached_classify(classifier)
    assert wrapped("repo", "Fix bug") == "tool"


def test_cached_classify_calls_fn_only_once_for_same_input(tmp_path: Path) -> None:
    classifier = _make_classifier("library")
    wrapped = cached_classify(classifier, cache_path=tmp_path / "cache.json")
    wrapped("repo", "Add feature")
    wrapped("repo", "Add feature")
    classifier.assert_called_once()


def test_cached_classify_calls_fn_for_different_inputs(tmp_path: Path) -> None:
    classifier = _make_classifier("app")
    wrapped = cached_classify(classifier, cache_path=tmp_path / "cache.json")
    wrapped("repo", "Fix bug")
    wrapped("repo", "Add tests")
    assert classifier.call_count == 2


def test_cached_classify_persists_across_instances(tmp_path: Path) -> None:
    cache_file = tmp_path / "cache.json"
    classifier = _make_classifier("tool")

    cached_classify(classifier, cache_path=cache_file)("repo", "Fix bug")
    classifier.reset_mock()

    cached_classify(classifier, cache_path=cache_file)("repo", "Fix bug")
    classifier.assert_not_called()


# ── make_enriched_classifier ──────────────────────────────────────────────────


def test_make_enriched_classifier_returns_enriched_pr() -> None:
    classify_fn = make_enriched_classifier(
        _make_classifier("biblioteca"),
        _make_classifier("bug fix"),
        _make_classifier("boa"),
    )
    result = classify_fn(_make_pr())
    assert isinstance(result, EnrichedPR)
    assert result.project_type == "biblioteca"
    assert result.contribution_nature == "bug fix"
    assert result.description_clarity == "boa"


def test_make_enriched_classifier_caches_same_pr() -> None:
    type_fn = _make_classifier("biblioteca")
    classify_fn = make_enriched_classifier(
        type_fn, _make_classifier("bug fix"), _make_classifier("boa")
    )
    pr = _make_pr()
    classify_fn(pr)
    classify_fn(pr)
    type_fn.assert_called_once()


def test_make_enriched_classifier_persists_cache(tmp_path: Path) -> None:
    cache_file = tmp_path / "enrich_cache.json"
    type_fn = _make_classifier("ferramenta")

    make_enriched_classifier(
        type_fn,
        _make_classifier("feature"),
        _make_classifier("boa"),
        cache_path=cache_file,
    )(_make_pr())
    type_fn.reset_mock()

    make_enriched_classifier(
        type_fn,
        _make_classifier("feature"),
        _make_classifier("boa"),
        cache_path=cache_file,
    )(_make_pr())
    type_fn.assert_not_called()
