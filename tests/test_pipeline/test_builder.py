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


# ── TASK-26: build_pipeline() ────────────────────────────────────────────────
# Mocks: lambdas simples no lugar de PRRecord + filtros/mappers reais do dev2.
# No merge da Sprint 3, os testes de integração substituem estes mocks.

def test_build_pipeline_sem_filtros_sem_mappers() -> None:
    result = list(build_pipeline([1, 2, 3], filters=(), mappers=()))
    assert result == [1, 2, 3]


def test_build_pipeline_filtro_unico() -> None:
    is_even: callable = lambda x: x % 2 == 0
    result = list(build_pipeline([1, 2, 3, 4, 5], filters=(is_even,), mappers=()))
    assert result == [2, 4]


def test_build_pipeline_filtros_combinados() -> None:
    is_even: callable = lambda x: x % 2 == 0
    gt_two: callable = lambda x: x > 2
    result = list(build_pipeline([1, 2, 3, 4, 5, 6], filters=(is_even, gt_two), mappers=()))
    assert result == [4, 6]


def test_build_pipeline_mapper_unico() -> None:
    double: callable = lambda x: x * 2
    result = list(build_pipeline([1, 2, 3], filters=(), mappers=(double,)))
    assert result == [2, 4, 6]


def test_build_pipeline_filtro_depois_mapper() -> None:
    is_even: callable = lambda x: x % 2 == 0
    double: callable = lambda x: x * 2
    result = list(build_pipeline([1, 2, 3, 4, 5], filters=(is_even,), mappers=(double,)))
    assert result == [4, 8]


def test_build_pipeline_mappers_compostos() -> None:
    double: callable = lambda x: x * 2
    add_one: callable = lambda x: x + 1
    result = list(build_pipeline([1, 2, 3], filters=(), mappers=(double, add_one)))
    assert result == [3, 5, 7]


def test_build_pipeline_retorna_iteravel_lazy() -> None:
    calls: list[int] = []

    def rastrear(x: int) -> int:
        calls.append(x)
        return x

    result = build_pipeline(range(1000), filters=(), mappers=(rastrear,))
    assert not isinstance(result, (list, tuple))
    next(iter(result))
    assert len(calls) == 1


def test_build_pipeline_source_vazio() -> None:
    is_even: callable = lambda x: x % 2 == 0
    result = list(build_pipeline([], filters=(is_even,), mappers=()))
    assert result == []
