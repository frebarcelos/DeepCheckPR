"""Heurísticas de pré-classificação para PRs — módulo PURO (zero I/O).

Detecta casos obvios antes de chamar o LLM, eliminando 10-30% das chamadas.
Todas as funções são puras: sem I/O, sem estado global mutável.
"""

import re

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.transforms.reducers import EnrichedPR

# frozensets são imutáveis — não violam BP005
_BUG_KEYWORDS: frozenset[str] = frozenset(
    {"bug", "crash", "error", "patch", "hotfix", "revert"}
)
_FEAT_KEYWORDS: frozenset[str] = frozenset(
    {"add", "implement", "feature", "support", "introduce", "create"}
)
_DOC_KEYWORDS: frozenset[str] = frozenset(
    {"doc", "docs", "readme", "changelog", "comment", "typo", "spelling", "grammar"}
)
_REFAC_KEYWORDS: frozenset[str] = frozenset(
    {"refactor", "clean", "cleanup", "rename", "move", "reorganize", "restructure"}
)

_WORD_RE: re.Pattern[str] = re.compile(r"\b\w+\b")


def heuristic_nature(title: str) -> str | None:
    """Infere a natureza da contribuição pelo título do PR.

    Extrai palavras ignorando pontuação (ex: "hotfix:" → "hotfix").
    Verifica keywords de domínio mais específico antes dos genéricos:
    doc → refatoração → bug → feature.

    Returns:
        Uma das naturezas do frozenset canônico, ou None se incerto.
    """
    words = frozenset(_WORD_RE.findall(title.lower()))
    if words & _DOC_KEYWORDS:
        return "documentação"
    if words & _REFAC_KEYWORDS:
        return "refatoração"
    if words & _BUG_KEYWORDS:
        return "bug fix"
    if words & _FEAT_KEYWORDS:
        return "feature"
    return None


def heuristic_clarity(body: str) -> str | None:
    """Infere a clareza do corpo do PR.

    Só determina clareza no caso trivial: body vazio → insuficiente.
    Qualquer conteúdo não-vazio requer LLM para avaliar qualidade.

    Returns:
        "insuficiente" se body vazio, None se body tem conteúdo.
    """
    if not body.strip():
        return "insuficiente"
    return None


def heuristic_classify(pr: PRRecord) -> EnrichedPR | None:
    """Classifica o PR via heurística, sem chamar o LLM.

    Retorna EnrichedPR apenas quando há certeza suficiente:
    - Título e body vazios → defaults conservadores.
    - Body vazio + natureza identificável pelo título → clareza=insuficiente.

    Retorna None nos demais casos (body com conteúdo, título ambíguo),
    deixando a decisão para o LLM.

    O campo project_type é sempre "outro" — depende do repositório
    e não é inferível pelo título/body isoladamente.
    """
    clarity = heuristic_clarity(pr.body)
    if clarity is None:
        return None

    title_empty = not pr.title.strip()
    nature = heuristic_nature(pr.title)

    if title_empty or nature is not None:
        return EnrichedPR(
            pr=pr,
            project_type="outro",
            contribution_nature=nature if nature is not None else "outro",
            description_clarity=clarity,
        )
    return None
