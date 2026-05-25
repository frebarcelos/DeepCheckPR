import pytest

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.pipeline.builder import (
    EnrichedPR,
    build_pipeline,
    compose,
    enrich_pipeline,
    pipe,
    pipeline_from_env,
    stats_pipeline,
)


def _make_pr(pr_id: int = 1, language: str = "python") -> PRRecord:
    return PRRecord(
        pr_id=pr_id,
        repo_name="org/repo",
        language=language,
        title="Fix bug",
        body="Some body text.",
        state="merged",
        created_at="2024-01-01",
        merged_at="2024-01-02",
        additions=5,
        deletions=2,
        changed_files=1,
    )


def _classify(pr: PRRecord) -> EnrichedPR:
    return EnrichedPR(
        pr=pr,
        project_type="biblioteca",
        contribution_nature="bug fix",
        description_clarity="boa",
    )


# ── TASK-25: compose() ────────────────────────────────────────────────────────


def test_compose_returns_callable() -> None:
    assert callable(compose(str))


def test_compose_no_args_is_identity() -> None:
    assert compose()(42) == 42


def test_compose_single_fn() -> None:
    double = lambda x: x * 2
    assert compose(double)(3) == 6


def test_compose_two_fns() -> None:
    double = lambda x: x * 2
    add_one = lambda x: x + 1
    assert compose(double, add_one)(3) == 7


def test_compose_three_fns() -> None:
    double = lambda x: x * 2
    add_one = lambda x: x + 1
    negate = lambda x: -x
    assert compose(double, add_one, negate)(3) == -7


# ── TASK-25: pipe() ───────────────────────────────────────────────────────────


def test_pipe_no_fns_returns_value() -> None:
    assert pipe(42) == 42


def test_pipe_single_fn() -> None:
    double = lambda x: x * 2
    assert pipe(3, double) == 6


def test_pipe_two_fns() -> None:
    double = lambda x: x * 2
    add_one = lambda x: x + 1
    assert pipe(3, double, add_one) == 7


def test_pipe_three_fns() -> None:
    double = lambda x: x * 2
    add_one = lambda x: x + 1
    negate = lambda x: -x
    assert pipe(3, double, add_one, negate) == -7


def test_pipe_consistent_with_compose() -> None:
    double = lambda x: x * 2
    add_one = lambda x: x + 1
    assert pipe(3, double, add_one) == compose(double, add_one)(3)


# ── TASK-26: build_pipeline() ────────────────────────────────────────────────
# Mocks: lambdas simples no lugar de PRRecord + filtros/mappers reais do dev2.
# No merge da Sprint 3, os testes de integração substituem estes mocks.


def test_build_pipeline_sem_filtros_sem_mappers() -> None:
    result = list(build_pipeline([1, 2, 3], filters=(), mappers=()))
    assert result == [1, 2, 3]


def test_build_pipeline_filtro_unico() -> None:
    is_even = lambda x: x % 2 == 0
    result = list(build_pipeline([1, 2, 3, 4, 5], filters=(is_even,), mappers=()))
    assert result == [2, 4]


def test_build_pipeline_filtros_combinados() -> None:
    is_even = lambda x: x % 2 == 0
    gt_two = lambda x: x > 2
    result = list(
        build_pipeline([1, 2, 3, 4, 5, 6], filters=(is_even, gt_two), mappers=())
    )
    assert result == [4, 6]


def test_build_pipeline_mapper_unico() -> None:
    double = lambda x: x * 2
    result = list(build_pipeline([1, 2, 3], filters=(), mappers=(double,)))
    assert result == [2, 4, 6]


def test_build_pipeline_filtro_depois_mapper() -> None:
    is_even = lambda x: x % 2 == 0
    double = lambda x: x * 2
    result = list(
        build_pipeline([1, 2, 3, 4, 5], filters=(is_even,), mappers=(double,))
    )
    assert result == [4, 8]


def test_build_pipeline_mappers_compostos() -> None:
    double = lambda x: x * 2
    add_one = lambda x: x + 1
    result = list(build_pipeline([1, 2, 3], filters=(), mappers=(double, add_one)))
    assert result == [3, 5, 7]


def test_build_pipeline_retorna_iteravel_lazy() -> None:
    calls: list[int] = []

    def rastrear(x: int) -> int:
        calls.append(x)
        return x

    result = build_pipeline(range(1000), filters=(), mappers=(rastrear,))
    assert not isinstance(result, list | tuple)
    next(iter(result))
    assert len(calls) == 1


def test_build_pipeline_source_vazio() -> None:
    is_even = lambda x: x % 2 == 0
    result = list(build_pipeline([], filters=(is_even,), mappers=()))
    assert result == []


# ── enrich_pipeline ───────────────────────────────────────────────────────────


def test_enrich_pipeline_applies_classify_fn() -> None:
    prs = [_make_pr(1), _make_pr(2)]
    result = list(enrich_pipeline(prs, _classify))
    assert len(result) == 2
    assert all(r.project_type == "biblioteca" for r in result)


def test_enrich_pipeline_preserves_original_pr() -> None:
    pr = _make_pr(42)
    result = list(enrich_pipeline([pr], _classify))
    assert result[0].pr == pr


def test_enrich_pipeline_empty_source() -> None:
    assert list(enrich_pipeline([], _classify)) == []


def test_enrich_pipeline_is_lazy() -> None:
    calls: list[int] = []

    def counting_classify(pr: PRRecord) -> EnrichedPR:
        calls.append(1)
        return _classify(pr)

    pipeline = enrich_pipeline(iter([_make_pr(), _make_pr()]), counting_classify)
    assert not isinstance(pipeline, list | tuple)
    next(iter(pipeline))
    assert len(calls) == 1


# ── stats_pipeline ────────────────────────────────────────────────────────────


def test_stats_pipeline_returns_stats_for_each_pr() -> None:
    prs = [_make_pr(1), _make_pr(2), _make_pr(3)]
    result = list(stats_pipeline(prs))
    assert len(result) == 3


def test_stats_pipeline_computes_correct_total_changes() -> None:
    pr = _make_pr()
    result = list(stats_pipeline([pr]))
    assert result[0].total_changes == 7  # additions=5 + deletions=2 from _make_pr()


def test_stats_pipeline_empty_source() -> None:
    assert list(stats_pipeline([])) == []


def test_stats_pipeline_is_lazy() -> None:
    pipeline = stats_pipeline(iter([_make_pr(), _make_pr()]))
    assert not isinstance(pipeline, list | tuple)
    next(iter(pipeline))


# ── pipeline_from_env (ISSUE-46) ──────────────────────────────────────────────


def _make_pr_state(state: str, additions: int = 5, deletions: int = 2) -> PRRecord:
    return PRRecord(
        pr_id=1,
        repo_name="org/repo",
        language="python",
        title="Fix bug",
        body="Body.",
        state=state,
        created_at="2024-01-01",
        merged_at="2024-01-02",
        additions=additions,
        deletions=deletions,
        changed_files=1,
    )


def test_pipeline_from_env_sem_vars_passa_tudo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FILTER_STATE", raising=False)
    monkeypatch.delenv("MIN_CHANGES", raising=False)
    monkeypatch.delenv("ENABLE_LLM", raising=False)
    prs = [_make_pr_state("merged"), _make_pr_state("open")]
    assert list(pipeline_from_env(iter(prs))) == prs


def test_pipeline_from_env_filter_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FILTER_STATE", "merged")
    monkeypatch.delenv("MIN_CHANGES", raising=False)
    monkeypatch.delenv("ENABLE_LLM", raising=False)
    prs = [_make_pr_state("merged"), _make_pr_state("open")]
    result = list(pipeline_from_env(iter(prs)))
    assert len(result) == 1
    assert result[0].state == "merged"


def test_pipeline_from_env_min_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FILTER_STATE", raising=False)
    monkeypatch.setenv("MIN_CHANGES", "10")
    monkeypatch.delenv("ENABLE_LLM", raising=False)
    prs = [
        _make_pr_state("merged", additions=3, deletions=2),
        _make_pr_state("merged", additions=8, deletions=5),
    ]
    result = list(pipeline_from_env(iter(prs)))
    assert len(result) == 1
    assert (result[0].additions or 0) + (result[0].deletions or 0) >= 10


def test_pipeline_from_env_filtros_combinados(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FILTER_STATE", "merged")
    monkeypatch.setenv("MIN_CHANGES", "10")
    monkeypatch.delenv("ENABLE_LLM", raising=False)
    prs = [
        _make_pr_state("merged", additions=8, deletions=5),
        _make_pr_state("merged", additions=2, deletions=1),
        _make_pr_state("open", additions=8, deletions=5),
    ]
    result = list(pipeline_from_env(iter(prs)))
    assert len(result) == 1
    assert result[0].state == "merged"


def test_pipeline_from_env_enable_llm_com_fn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FILTER_STATE", raising=False)
    monkeypatch.delenv("MIN_CHANGES", raising=False)
    monkeypatch.setenv("ENABLE_LLM", "true")
    pr = _make_pr_state("merged")
    result = list(pipeline_from_env(iter([pr]), classify_fn=_classify))
    assert isinstance(result[0], EnrichedPR)


def test_pipeline_from_env_enable_llm_sem_fn_nao_aplica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FILTER_STATE", raising=False)
    monkeypatch.delenv("MIN_CHANGES", raising=False)
    monkeypatch.setenv("ENABLE_LLM", "true")
    pr = _make_pr_state("merged")
    result = list(pipeline_from_env(iter([pr])))
    assert result[0] == pr


def test_pipeline_from_env_enable_llm_false_ignora_fn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FILTER_STATE", raising=False)
    monkeypatch.delenv("MIN_CHANGES", raising=False)
    monkeypatch.setenv("ENABLE_LLM", "false")
    pr = _make_pr_state("merged")
    result = list(pipeline_from_env(iter([pr]), classify_fn=_classify))
    assert result[0] == pr


def test_pipeline_from_env_e_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FILTER_STATE", raising=False)
    monkeypatch.delenv("MIN_CHANGES", raising=False)
    monkeypatch.delenv("ENABLE_LLM", raising=False)
    result = pipeline_from_env(iter([_make_pr_state("merged")]))
    assert not isinstance(result, list | tuple)


def test_pipeline_from_env_source_vazio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FILTER_STATE", "merged")
    monkeypatch.setenv("MIN_CHANGES", "5")
    monkeypatch.delenv("ENABLE_LLM", raising=False)
    assert list(pipeline_from_env(iter([]))) == []
