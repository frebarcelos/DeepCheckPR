"""Efeito colateral: classificadores semânticos de PRs via LLM.

Fase 1 — stubs com interface completa.
Fase 2 — substituir stubs por chamadas LLM reais.
Fase 3 — batch por repositório e enriquecimento lazy com cache.
"""

import json
from collections.abc import Callable, Iterable
from pathlib import Path

from pr_analyzer.cache.memo import make_enriched_classifier
from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.llm.client import LLMClient
from pr_analyzer.transforms.reducers import EnrichedPR

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
        result = str(data.get("tipo_projeto", "")).lower()
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
        result = str(data.get("natureza", "")).lower()
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


# ── Batch e enriquecimento (Fase 3) ───────────────────────────────────────────


def classify_repos_batch(
    groups: dict[str, list[PRRecord]],
    client: LLMClient,
) -> dict[str, str]:
    """Classifica o tipo de projeto de cada repositório com 1 chamada LLM por repo.

    Recebe o resultado de group_by_repo() e envia os títulos dos PRs de cada
    grupo como amostra para o classificador, evitando chamadas redundantes por PR.

    Args:
        groups: dicionário repo_name -> lista de PRs do repositório.
        client: cliente LLM para chamadas semânticas.

    Returns:
        Dicionário repo_name -> tipo_projeto.
    """

    def _classify_repo(item: tuple[str, list[PRRecord]]) -> tuple[str, str]:
        repo_name, prs = item
        titles = [pr.title for pr in prs]
        return (repo_name, classificar_tipo_projeto(repo_name, titles, client))

    return dict(map(_classify_repo, groups.items()))


def enrich_prs(
    prs: Iterable[PRRecord],
    client: LLMClient,
    cache_path: Path | None = None,
) -> Iterable[EnrichedPR]:
    """Aplica os 3 classificadores a cada PR via map(), retornando EnrichedPRs lazy.

    Usa make_enriched_classifier para envolver os classificadores com cache
    em memória e em disco. A avaliação é lazy: o LLM só é chamado ao consumir
    o iterável retornado.

    Args:
        prs: iterável de PRRecords a enriquecer.
        client: cliente LLM para chamadas semânticas.
        cache_path: caminho base para persistência do cache em disco (opcional).

    Returns:
        Iterável lazy de EnrichedPR.
    """

    def type_fn(repo: str, title: str) -> str:
        return classificar_tipo_projeto(repo, [title], client)

    def nature_fn(title: str, body: str) -> str:
        return classificar_natureza_contribuicao(title, body, client)

    def clarity_fn(body: str) -> str:
        return avaliar_clareza_descricao(body, client)

    classify = make_enriched_classifier(
        type_fn, nature_fn, clarity_fn, cache_path=cache_path
    )
    return map(classify, prs)


# ── safe_classify HOF (TASK-44) ───────────────────────────────────────────────


def safe_classify(
    classifier_fn: Callable[..., str],
    fallback: str,
    valid_values: frozenset[str] | None = None,
) -> Callable[..., str]:
    """HOF que envolve um classificador com tratamento de saída inválida.

    Se o classificador lançar qualquer exceção, ou retornar um valor fora de
    valid_values (quando fornecido), retorna fallback sem propagar o erro.

    Args:
        classifier_fn: função classificadora a envolver.
        fallback: valor retornado em caso de saída inválida ou exceção.
        valid_values: conjunto de valores aceitos; None desativa a validação.

    Returns:
        Callable com a mesma assinatura de classifier_fn.
    """

    def wrapper(*args: str) -> str:
        try:
            result = classifier_fn(*args)
            if valid_values is not None and result not in valid_values:
                return fallback
            return result
        except Exception:
            return fallback

    return wrapper


# ── English aliases (consumed by pipeline_bridge and external modules) ────────
classify_project_type = classificar_tipo_projeto
classify_contribution_nature = classificar_natureza_contribuicao
classify_description_clarity = avaliar_clareza_descricao
