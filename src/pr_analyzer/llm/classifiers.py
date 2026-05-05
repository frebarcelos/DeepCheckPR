"""Efeito colateral: classificadores semânticos de PRs via LLM.

Fase 1 — stubs com interface completa.
Fase 2 — substituir stubs por chamadas LLM reais.
"""

from pr_analyzer.llm.client import LLMClient

# ── Valores válidos de cada classificação ─────────────────────────────────────

PROJECT_TYPES: frozenset[str] = frozenset({
    "biblioteca",
    "aplicação web",
    "framework",
    "ferramenta",
    "outro",
})

CONTRIBUTION_NATURES: frozenset[str] = frozenset({
    "bug fix",
    "feature",
    "refatoração",
    "documentação",
    "outro",
})

DESCRIPTION_CLARITY_LEVELS: frozenset[str] = frozenset({
    "insuficiente",
    "básica",
    "boa",
    "excelente",
})


# ── Classificadores ───────────────────────────────────────────────────────────


def classify_project_type(
    repo_name: str,
    sample_titles: list[str],
    client: LLMClient,
) -> str:
    """Classifica o tipo de projeto de um repositório.

    Args:
        repo_name: nome do repositório (ex: "django/django").
        sample_titles: amostra de títulos de PRs do repositório.
        client: cliente LLM para chamada semântica.

    Returns:
        Uma string pertencente a PROJECT_TYPES.

    Note:
        Stub — retorna "outro" até a implementação real na Fase 2.
    """
    return "outro"


def classify_contribution_nature(
    title: str,
    body: str,
    client: LLMClient,
) -> str:
    """Classifica a natureza da contribuição de um PR.

    Args:
        title: título do PR.
        body: primeiros 300 caracteres do corpo do PR.
        client: cliente LLM para chamada semântica.

    Returns:
        Uma string pertencente a CONTRIBUTION_NATURES.

    Note:
        Stub — retorna "outro" até a implementação real na Fase 2.
    """
    return "outro"


def classify_description_clarity(
    body: str,
    client: LLMClient,
) -> str:
    """Avalia a clareza da descrição de um PR.

    Body vazio deve retornar "insuficiente" sem chamar o LLM (Fase 2).

    Args:
        body: primeiros 500 caracteres do corpo do PR.
        client: cliente LLM para chamada semântica.

    Returns:
        Uma string pertencente a DESCRIPTION_CLARITY_LEVELS.

    Note:
        Stub — retorna "insuficiente" até a implementação real na Fase 2.
    """
    return "insuficiente"
