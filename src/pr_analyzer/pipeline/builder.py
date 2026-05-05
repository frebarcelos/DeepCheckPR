from functools import reduce
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


def compose(*fns: Callable) -> Callable:
    """compose(f, g, h)(x) == h(g(f(x))). Sem args retorna identidade."""
    if not fns:
        return lambda x: x
    return reduce(lambda f, g: lambda x: g(f(x)), fns)


def pipe(value: T, *fns: Callable) -> T:
    """pipe(x, f, g, h) == h(g(f(x))). Sem fns retorna value."""
    return reduce(lambda acc, f: f(acc), fns, value)


def build_pipeline(
    source: Iterable,
    filters: tuple[Callable, ...] = (),
    mappers: tuple[Callable, ...] = (),
) -> Iterable:
    """Pipeline lazy: aplica filters com filter() e mappers com map() sobre source."""
    filtered = reduce(lambda s, f: filter(f, s), filters, source)
    return reduce(lambda s, m: map(m, s), mappers, filtered)
