from collections.abc import Callable
from typing import Any


def by_state(state: str) -> Callable[[Any], bool]:
    """
    Retorna um predicado que verifica se o estado de um PR corresponde ao estado fornecido.
    A comparação não diferencia maiúsculas de minúsculas.

    Args:
        state (str): O estado do Pull Request para filtrar.

    Returns:
        Callable[[Any], bool]: Uma função predicado que retorna True se o estado do PR corresponder.
    """
    target_state = state.lower()

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "state") or pr.state is None:
            return False
        return str(pr.state).lower() == target_state

    return predicate


def by_language(language: str) -> Callable[[Any], bool]:
    """
    Retorna um predicado que verifica se a linguagem de um PR corresponde à linguagem fornecida.
    A comparação não diferencia maiúsculas de minúsculas.

    Args:
        language (str): A linguagem de programação para filtrar.

    Returns:
        Callable[[Any], bool]: Uma função predicado que retorna True se a linguagem do PR corresponder.
    """
    target_language = language.lower()

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "language") or pr.language is None:
            return False
        return str(pr.language).lower() == target_language

    return predicate


def by_date_range(start: str, end: str) -> Callable[[Any], bool]:
    """
    Retorna um predicado que verifica se a data de criação de um PR está dentro
    do intervalo fornecido (inclusivo). Espera strings no formato ISO 8601.

    Args:
        start (str): A data inicial do intervalo.
        end (str): A data final do intervalo.

    Returns:
        Callable[[Any], bool]: Uma função predicado que retorna True se a data de criação do PR estiver no intervalo.
    """

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "created_at") or pr.created_at is None:
            return False
        pr_date = str(pr.created_at)[:10]
        return start <= pr_date <= end

    return predicate


def with_non_empty_body() -> Callable[[Any], bool]:
    """
    Retorna um predicado que verifica se um PR possui um corpo (descrição) não vazio.

    Returns:
        Callable[[Any], bool]: Uma função predicado que retorna True se o corpo do PR não for vazio.
    """

    def predicate(pr: Any) -> bool:
        if not hasattr(pr, "body") or pr.body is None:
            return False
        return str(pr.body).strip() != ""

    return predicate


def with_min_size(min_changes: int) -> Callable[[Any], bool]:
    """
    Retorna um predicado que verifica se o tamanho total (adições + exclusões)
    de um PR é maior ou igual a min_changes.

    Args:
        min_changes (int): O número mínimo de mudanças (adições e deleções combinadas).

    Returns:
        Callable[[Any], bool]: Uma função predicado que retorna True se o PR possuir tamanho maior ou igual ao mínimo.
    """

    def predicate(pr: Any) -> bool:
        additions = getattr(pr, "additions", 0) or 0
        deletions = getattr(pr, "deletions", 0) or 0
        try:
            return (int(additions) + int(deletions)) >= min_changes
        except (ValueError, TypeError):
            return False

    return predicate


def combine_filters(*predicates: Callable[[Any], bool]) -> Callable[[Any], bool]:
    """
    Combina múltiplos predicados utilizando o operador lógico AND (all).
    Se nenhum predicado for fornecido, retorna True para qualquer PR.

    Args:
        *predicates (Callable[[Any], bool]): Um número variável de funções predicado.

    Returns:
        Callable[[Any], bool]: Uma função predicado combinada que retorna True apenas se todos os predicados retornarem True.
    """

    def predicate(pr: Any) -> bool:
        return all(p(pr) for p in predicates)

    return predicate
