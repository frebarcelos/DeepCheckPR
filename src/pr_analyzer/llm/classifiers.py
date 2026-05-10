"""Efeito colateral: classificadores semânticos de PRs via LLM.

Fase 1 — stubs com interface completa.
Fase 2 — substituir stubs por chamadas LLM reais.
"""

import json

from pr_analyzer.llm.client import LLMClient

# ── Valores válidos de cada classificação ─────────────────────────────────────

TIPOS_PROJETO: frozenset[str] = frozenset(
    {
        "biblioteca",
        "aplicação web",
        "framework",
        "ferramenta",
        "outro",
    }
)

NATUREZAS_CONTRIBUICAO: frozenset[str] = frozenset(
    {
        "bug fix",
        "feature",
        "refatoração",
        "documentação",
        "outro",
    }
)

NIVEIS_CLAREZA_DESCRICAO: frozenset[str] = frozenset(
    {
        "insuficiente",
        "básica",
        "boa",
        "excelente",
    }
)


# ── Classificadores ───────────────────────────────────────────────────────────


def classificar_tipo_projeto(
    nome_repositorio: str,
    titulos_amostra: list[str],
    cliente: LLMClient,
) -> str:
    """Classifica o tipo de projeto de um repositório.

    Args:
        nome_repositorio: nome do repositório (ex: "django/django").
        titulos_amostra: amostra de títulos de PRs do repositório.
        cliente: cliente LLM para chamada semântica.

    Returns:
        Uma string pertencente a TIPOS_PROJETO.
    """
    prompt = f"Repositório: {nome_repositorio}. Títulos de PR: {titulos_amostra}.\n"
    prompt += 'Responda estritamente em formato JSON: {"tipo_projeto": "..."}. '
    prompt += f"Escolha uma das seguintes opções: {', '.join(TIPOS_PROJETO)}."

    try:
        response = cliente.run(prompt)
        data = json.loads(response.content)
        result = data.get("tipo_projeto", "").lower()
        if result in TIPOS_PROJETO:
            return result
    except Exception:
        pass

    return "outro"


def classificar_natureza_contribuicao(
    titulo: str,
    corpo: str,
    cliente: LLMClient,
) -> str:
    """Classifica a natureza da contribuição de um PR.

    Args:
        titulo: título do PR.
        corpo: primeiros 300 caracteres do corpo do PR.
        cliente: cliente LLM para chamada semântica.

    Returns:
        Uma string pertencente a NATUREZAS_CONTRIBUICAO.
    """
    corpo_cortado = corpo[:300]
    prompt = f"Título do PR: {titulo}\nCorpo: {corpo_cortado}\n"
    prompt += 'Responda estritamente em formato JSON: {"natureza": "..."}. '
    prompt += f"Escolha uma das seguintes opções: {', '.join(NATUREZAS_CONTRIBUICAO)}."

    try:
        response = cliente.run(prompt)
        data = json.loads(response.content)
        result = data.get("natureza", "").lower()
        if result in NATUREZAS_CONTRIBUICAO:
            return result
    except Exception:
        pass

    return "outro"


def avaliar_clareza_descricao(
    corpo: str,
    cliente: LLMClient,
) -> str:
    """Avalia a clareza da descrição de um PR.

    Body vazio deve retornar "insuficiente" sem chamar o LLM (Fase 2).

    Args:
        corpo: primeiros 500 caracteres do corpo do PR.
        cliente: cliente LLM para chamada semântica.

    Returns:
        Uma string pertencente a NIVEIS_CLAREZA_DESCRICAO.
    """
    if not corpo.strip():
        return "insuficiente"

    corpo_cortado = corpo[:500]
    prompt = f"Avalie a clareza deste corpo de PR: {corpo_cortado}\n"
    prompt += f"Responda apenas com uma das seguintes opções: {', '.join(NIVEIS_CLAREZA_DESCRICAO)}."

    try:
        response = cliente.run(prompt)
        result = str(response.content).strip().lower()

        for nivel in NIVEIS_CLAREZA_DESCRICAO:
            if nivel in result:
                return nivel
    except Exception:
        pass

    return "insuficiente"
