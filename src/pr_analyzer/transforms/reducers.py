"""Funções de transformação puras para agregar dados de PR utilizando reduções."""

from collections.abc import Callable, Iterable
from functools import reduce
from typing import Any, NamedTuple

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.mappers import PRStats


class EnrichedPR(NamedTuple):
    """PRRecord enriquecido com classificações semânticas via LLM."""

    pr: PRRecord
    project_type: str
    contribution_nature: str
    description_clarity: str
    review_complexity: str = ""


__all__: tuple[str, ...] = (
    "EnrichedPR",
    "count_by_field",
    "count_by_language",
    "count_by_project_type",
    "count_by_contribution_nature",
    "count_by_description_clarity",
    "count_by_review_complexity",
    "group_by_repo",
    "accumulate_stats",
    "aggregate_stats",
)


def count_by_field(field: str) -> Callable[[Iterable[Any]], dict[str, int]]:
    """
    Cria uma função de redução para contar as ocorrências de um campo específico.

    Args:
        field (str): O nome do atributo ou campo pelo qual agrupar e contar.

    Returns:
        Callable[[Iterable[Any]], dict[str, int]]: Uma função que recebe um iterável de itens e
            retorna um dicionário mapeando os valores do campo para a contagem de ocorrências.
    """
    return lambda items: reduce(
        lambda acc, item: acc
        | {getattr(item, field): acc.get(getattr(item, field), 0) + 1},
        items,
        {},
    )


def count_by_language(prs: Iterable[PRRecord]) -> dict[str, int]:
    """
    Conta o número de PRs por linguagem utilizando uma redução pura.

    Args:
        prs (Iterable[PRRecord]): Um iterável de registros de Pull Requests.

    Returns:
        dict[str, int]: Um dicionário mapeando nomes das linguagens para as suas contagens.
    """
    return count_by_field("language")(prs)


def count_by_project_type(enriched_prs: Iterable[EnrichedPR]) -> dict[str, int]:
    """
    Conta o número de PRs por tipo de projeto.

    Args:
        enriched_prs (Iterable[EnrichedPR]): Um iterável de Pull Requests enriquecidos.

    Returns:
        dict[str, int]: Um dicionário mapeando os tipos de projeto para as suas contagens.
    """
    return count_by_field("project_type")(enriched_prs)


def count_by_contribution_nature(enriched_prs: Iterable[EnrichedPR]) -> dict[str, int]:
    """
    Conta o número de PRs por natureza de contribuição.

    Args:
        enriched_prs (Iterable[EnrichedPR]): Um iterável de Pull Requests enriquecidos.

    Returns:
        dict[str, int]: Um dicionário mapeando as naturezas de contribuição para as suas contagens.
    """
    return count_by_field("contribution_nature")(enriched_prs)


def count_by_description_clarity(enriched_prs: Iterable[EnrichedPR]) -> dict[str, int]:
    """
    Conta o número de PRs por nível de clareza da descrição.

    Args:
        enriched_prs (Iterable[EnrichedPR]): Um iterável de Pull Requests enriquecidos.

    Returns:
        dict[str, int]: Um dicionário mapeando os níveis de clareza para as suas contagens.
    """
    return count_by_field("description_clarity")(enriched_prs)


def count_by_review_complexity(enriched_prs: Iterable[EnrichedPR]) -> dict[str, int]:
    """
    Conta o número de PRs por nível de complexidade de revisão.

    Args:
        enriched_prs (Iterable[EnrichedPR]): Um iterável de Pull Requests enriquecidos.

    Returns:
        dict[str, int]: Um dicionário mapeando os níveis de complexidade para as suas contagens.
    """
    return count_by_field("review_complexity")(enriched_prs)


def group_by_repo(prs: Iterable[PRRecord]) -> dict[str, list[PRRecord]]:
    """
    Agrupa PRs pelo nome do repositório utilizando uma redução pura.

    Args:
        prs (Iterable[PRRecord]): Um iterável de registros de Pull Requests.

    Returns:
        dict[str, list[PRRecord]]: Um dicionário mapeando os nomes dos repositórios para listas de PRRecords.
    """
    return reduce(
        lambda acc, pr: acc | {pr.repo_name: [*acc.get(pr.repo_name, []), pr]},
        prs,
        {},
    )


def accumulate_stats(stats: Iterable[PRStats]) -> dict[str, int]:
    """
    Acumula os totais e a contagem para uma coleção de PRStats em uma única passagem.

    Args:
        stats (Iterable[PRStats]): Um iterável de estatísticas de Pull Requests.

    Returns:
        dict[str, int]: Um dicionário contendo totais para caracteres, palavras,
            alterações, mesclagens e a contagem de itens.
    """
    return reduce(
        lambda acc, stat: {
            "chars": stat.body_char_count + acc["chars"],
            "words": stat.body_word_count + acc["words"],
            "changes": stat.total_changes + acc["changes"],
            "merges": int(stat.is_merged) + acc["merges"],
            "count": acc["count"] + 1,
        },
        stats,
        {"chars": 0, "words": 0, "changes": 0, "merges": 0, "count": 0},
    )


def aggregate_stats(stats: Iterable[PRStats]) -> dict[str, float]:
    """
    Calcula as estatísticas médias para uma coleção de PRStats.

    Args:
        stats (Iterable[PRStats]): Um iterável de estatísticas de Pull Requests.

    Returns:
        dict[str, float]: Um dicionário com as médias de caracteres (avg_chars),
            palavras (avg_words), alterações (avg_changes) e a taxa de mesclagem (merge_rate).
    """
    acc = accumulate_stats(stats)
    count = acc["count"]

    if count == 0:
        return {
            "avg_chars": 0.0,
            "avg_words": 0.0,
            "avg_changes": 0.0,
            "merge_rate": 0.0,
        }

    return {
        "avg_chars": acc["chars"] / count,
        "avg_words": acc["words"] / count,
        "avg_changes": acc["changes"] / count,
        "merge_rate": acc["merges"] / count,
    }
