import os
from collections.abc import Callable, Iterable
from functools import reduce
from typing import Any, TypeVar

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.filters import by_state, with_min_size
from pr_analyzer.transforms.mappers import PRStats, compute_stats
from pr_analyzer.transforms.reducers import EnrichedPR

__all__: tuple[str, ...] = (
    "EnrichedPR",
    "build_pipeline",
    "compose",
    "enrich_pipeline",
    "pipe",
    "pipeline_from_env",
    "stats_pipeline",
)

T = TypeVar("T")


def compose(*fns: Callable[..., Any]) -> Callable[..., Any]:
    """compose(f, g, h)(x) == h(g(f(x))). Sem args retorna identidade."""
    if not fns:
        return lambda x: x
    return reduce(lambda f, g: lambda x: g(f(x)), fns)


def pipe(value: T, *fns: Callable[..., Any]) -> T:
    """pipe(x, f, g, h) == h(g(f(x))). Sem fns retorna value."""
    return reduce(lambda acc, f: f(acc), fns, value)


def enrich_pipeline(
    prs: Iterable[PRRecord],
    classify_fn: Callable[[PRRecord], EnrichedPR],
) -> Iterable[EnrichedPR]:
    """Aplica classify_fn sobre cada PR de forma lazy, retornando EnrichedPRs."""
    return map(classify_fn, prs)


def stats_pipeline(prs: Iterable[PRRecord]) -> Iterable[PRStats]:
    """Mapeia compute_stats sobre cada PR de forma lazy."""
    return map(compute_stats, prs)


def build_pipeline(
    source: Iterable[Any],
    filters: tuple[Callable[..., Any], ...] = (),
    mappers: tuple[Callable[..., Any], ...] = (),
) -> Iterable[Any]:
    """Pipeline lazy: aplica filters com filter() e mappers com map() sobre source."""
    filtered = reduce(lambda s, f: filter(f, s), filters, source)
    return reduce(lambda s, m: map(m, s), mappers, filtered)


def pipeline_from_env(
    source: Iterable[PRRecord],
    classify_fn: Callable[[PRRecord], EnrichedPR] | None = None,
) -> Iterable[Any]:
    """Pipeline lazy configurado por variáveis de ambiente.

    FILTER_STATE: filtra PRs pelo estado (ex: "merged", "open"). Padrão: sem filtro.
    MIN_CHANGES:  mínimo de alterações (additions + deletions). Padrão: 0.
    ENABLE_LLM:   se "true" e classify_fn for fornecido, aplica enriquecimento LLM.
    """
    state = os.environ.get("FILTER_STATE", "").strip().lower()
    min_ch = int(os.environ.get("MIN_CHANGES", "0") or "0")
    enable_llm = os.environ.get("ENABLE_LLM", "false").lower() == "true"

    state_filter: tuple[Callable[..., Any], ...] = (by_state(state),) if state else ()
    size_filter: tuple[Callable[..., Any], ...] = (
        (with_min_size(min_ch),) if min_ch > 0 else ()
    )
    llm_mapper: tuple[Callable[..., Any], ...] = (
        (classify_fn,) if enable_llm and classify_fn is not None else ()
    )

    return build_pipeline(
        source,
        filters=state_filter + size_filter,
        mappers=llm_mapper,
    )
