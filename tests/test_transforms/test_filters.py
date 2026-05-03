from typing import NamedTuple

from pr_analyzer.transforms.filters import (
    by_date_range,
    by_language,
    by_state,
    combine_filters,
    with_min_size,
    with_non_empty_body,
)


class DummyPR(NamedTuple):
    state: str = ""
    language: str = ""
    created_at: str = ""
    body: str = ""
    additions: int = 0
    deletions: int = 0


def test_by_state_match() -> None:
    pr = DummyPR(state="OPEN", language="Python")
    predicate = by_state("open")
    assert predicate(pr)


def test_by_state_mismatch() -> None:
    pr = DummyPR(state="CLOSED", language="Python")
    predicate = by_state("open")
    assert not predicate(pr)


def test_by_state_case_insensitive() -> None:
    pr1 = DummyPR(state="OpEn", language="Python")
    pr2 = DummyPR(state="open", language="Python")
    predicate = by_state("OpeN")
    assert predicate(pr1)
    assert predicate(pr2)


def test_by_language_match() -> None:
    pr = DummyPR(state="OPEN", language="Python")
    predicate = by_language("python")
    assert predicate(pr)


def test_by_language_mismatch() -> None:
    pr = DummyPR(state="OPEN", language="Java")
    predicate = by_language("python")
    assert not predicate(pr)


def test_by_language_case_insensitive() -> None:
    pr1 = DummyPR(state="OPEN", language="pYtHoN")
    pr2 = DummyPR(state="OPEN", language="python")
    predicate = by_language("PyThon")
    assert predicate(pr1)
    assert predicate(pr2)


def test_by_date_range_inside() -> None:
    pr = DummyPR(created_at="2023-05-15T10:00:00Z")
    predicate = by_date_range("2023-05-01", "2023-05-31")
    assert predicate(pr)


def test_by_date_range_outside() -> None:
    pr = DummyPR(created_at="2023-06-01T10:00:00Z")
    predicate = by_date_range("2023-05-01", "2023-05-31")
    assert not predicate(pr)


def test_by_date_range_boundaries() -> None:
    pr_start = DummyPR(created_at="2023-05-01T00:00:00Z")
    pr_end = DummyPR(created_at="2023-05-31T23:59:59Z")
    predicate = by_date_range("2023-05-01", "2023-05-31")
    assert predicate(pr_start)
    assert predicate(pr_end)


def test_with_non_empty_body_valid() -> None:
    pr = DummyPR(body="Fixes a bug")
    predicate = with_non_empty_body()
    assert predicate(pr)


def test_with_non_empty_body_empty_or_spaces() -> None:
    pr1 = DummyPR(body="")
    pr2 = DummyPR(body="   \n  ")
    predicate = with_non_empty_body()
    assert not predicate(pr1)
    assert not predicate(pr2)


def test_with_min_size() -> None:
    pr = DummyPR(additions=50, deletions=20)
    predicate1 = with_min_size(50)
    predicate2 = with_min_size(100)
    assert predicate1(pr)
    assert not predicate2(pr)


def test_combine_filters_multiple() -> None:
    pr1 = DummyPR(state="OPEN", language="Python")
    pr2 = DummyPR(state="OPEN", language="Java")
    pr3 = DummyPR(state="CLOSED", language="Python")

    predicate = combine_filters(by_state("OPEN"), by_language("Python"))

    assert predicate(pr1)
    assert not predicate(pr2)
    assert not predicate(pr3)


def test_combine_filters_empty() -> None:
    pr = DummyPR(state="OPEN", language="Python")
    predicate = combine_filters()
    assert predicate(pr)
