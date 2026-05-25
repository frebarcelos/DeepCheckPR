"""Funções de transformação puras para mapear registros de PRs em metadados e estatísticas."""

from typing import NamedTuple

from pr_analyzer.io.csv_reader import PRRecord


class PRStats(NamedTuple):
    """Estatísticas de um único registro de Pull Request."""

    body_char_count: int
    body_word_count: int
    total_changes: int
    is_merged: bool


def compute_stats(pr: PRRecord) -> PRStats:
    """
    Calcula as estatísticas para um determinado registro de PR.

    Args:
        pr (PRRecord): O registro do Pull Request para o qual calcular as estatísticas.

    Returns:
        PRStats: Uma tupla nomeada PRStats contendo a contagem de caracteres, contagem de palavras,
            total de alterações (adições + exclusões) e um booleano indicando se o PR foi mesclado.
    """
    body_char_count = len(pr.body)
    body_word_count = len(pr.body.split())

    total_changes = (pr.additions or 0) + (pr.deletions or 0)
    is_merged = bool(pr.merged_at)

    return PRStats(
        body_char_count=body_char_count,
        body_word_count=body_word_count,
        total_changes=total_changes,
        is_merged=is_merged,
    )
