from typing import NamedTuple

from pr_analyzer.transforms.filters import by_language, by_state


class DummyPR(NamedTuple):
    state: str
    language: str


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
