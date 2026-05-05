import pytest

from pr_analyzer.pipeline.builder import build_pipeline, compose, pipe


# ── TASK-25: compose() ────────────────────────────────────────────────────────

def test_compose_returns_callable() -> None:
    assert callable(compose(str))


def test_compose_no_args_is_identity() -> None:
    assert compose()(42) == 42


def test_compose_single_fn() -> None:
    double: callable = lambda x: x * 2
    assert compose(double)(3) == 6


def test_compose_two_fns() -> None:
    double: callable = lambda x: x * 2
    add_one: callable = lambda x: x + 1
    assert compose(double, add_one)(3) == 7


def test_compose_three_fns() -> None:
    double: callable = lambda x: x * 2
    add_one: callable = lambda x: x + 1
    negate: callable = lambda x: -x
    assert compose(double, add_one, negate)(3) == -7


# ── TASK-25: pipe() ───────────────────────────────────────────────────────────

def test_pipe_no_fns_returns_value() -> None:
    assert pipe(42) == 42


def test_pipe_single_fn() -> None:
    double: callable = lambda x: x * 2
    assert pipe(3, double) == 6


def test_pipe_two_fns() -> None:
    double: callable = lambda x: x * 2
    add_one: callable = lambda x: x + 1
    assert pipe(3, double, add_one) == 7


def test_pipe_three_fns() -> None:
    double: callable = lambda x: x * 2
    add_one: callable = lambda x: x + 1
    negate: callable = lambda x: -x
    assert pipe(3, double, add_one, negate) == -7


def test_pipe_consistent_with_compose() -> None:
    double: callable = lambda x: x * 2
    add_one: callable = lambda x: x + 1
    assert pipe(3, double, add_one) == compose(double, add_one)(3)


# ── TASK-26: build_pipeline() — contrato (RED até TASK-26) ───────────────────

def test_build_pipeline_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        build_pipeline(iter([]), filters=(), mappers=())
