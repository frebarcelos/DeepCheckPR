from pathlib import Path
from unittest.mock import MagicMock

from pr_analyzer.cache.memo import cached_classify


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
