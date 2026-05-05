from collections.abc import Callable, Iterable
from functools import reduce
from typing import Any, TypeVar

T = TypeVar("T")


def compose(*fns: Callable[..., Any]) -> Callable[..., Any]:
    """compose(f, g, h)(x) == h(g(f(x))). Sem args retorna identidade."""
    if not fns:
        return lambda x: x
    return reduce(lambda f, g: lambda x: g(f(x)), fns)


def pipe(value: T, *fns: Callable[..., Any]) -> T:
    """pipe(x, f, g, h) == h(g(f(x))). Sem fns retorna value."""
    return reduce(lambda acc, f: f(acc), fns, value)


def build_pipeline(
    source: Iterable[Any],
    filters: tuple[Callable[..., Any], ...] = (),
    mappers: tuple[Callable[..., Any], ...] = (),
) -> Iterable[Any]:
    """Pipeline lazy: aplica filters com filter() e mappers com map() sobre source."""
    filtered = reduce(lambda s, f: filter(f, s), filters, source)
    return reduce(lambda s, m: map(m, s), mappers, filtered)
