from typing import Callable, TypeVar

T = TypeVar("T")


def compose(*fns: Callable) -> Callable:
    """Retorna uma função que aplica fns em sequência: compose(f, g)(x) == g(f(x))."""
    raise NotImplementedError


def pipe(value: T, *fns: Callable) -> T:
    """Aplica fns em sequência sobre value: pipe(x, f, g) == g(f(x))."""
    raise NotImplementedError


def build_pipeline(*steps: Callable) -> Callable:
    """Constrói um pipeline reutilizável a partir de steps funcionais."""
    raise NotImplementedError
