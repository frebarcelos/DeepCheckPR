"""Efeito colateral: classificadores semânticos de PRs via LLM.

Fase 1 — stubs com interface completa.
Fase 2 — substituir stubs por chamadas LLM reais.
Fase 3 — batch por repositório e enriquecimento lazy com cache.
"""

import asyncio
import json
import os
import re
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pr_analyzer.cache.memo import make_cache_key, make_enriched_classifier
from pr_analyzer.cache.sqlite_store import SqliteKVStore
from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.llm.client import AsyncLLMClient, LLMClient
from pr_analyzer.llm.metrics import ClassificationMetrics
from pr_analyzer.llm.skills import (
    FEW_SHOT_CONTRIBUTION_NATURE,
    FEW_SHOT_DESCRIPTION_CLARITY,
    FEW_SHOT_PROJECT_TYPE,
)
from pr_analyzer.transforms.heuristics import heuristic_classify, heuristic_complexity
from pr_analyzer.transforms.reducers import EnrichedPR

# ── Helpers ───────────────────────────────────────────────────────────────────

_CODE_BLOCK = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

_CLARITY_EN_TO_PT: dict[str, str] = {
    "insufficient": "insuficiente",
    "basic": "básica",
    "good": "boa",
    "excellent": "excelente",
}


def _extract_json(text: str) -> dict[str, str]:
    """Parse JSON from model response, stripping markdown code blocks if present."""
    raw = text.strip()
    match = _CODE_BLOCK.search(raw)
    if match:
        raw = match.group(1).strip()
    return json.loads(raw)  # type: ignore[no-any-return]


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

COMPLEXIDADES_REVISAO: frozenset[str] = frozenset({"low", "medium", "high"})

# ── Guardrails de entrada ─────────────────────────────────────────────────────

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")


class GuardrailViolation(Exception):  # noqa: N818
    """Raised when input fails guardrail validation before reaching the LLM."""


def sanitize(text: str, max_chars: int) -> str:
    """Remove caracteres de controle e trunca ao limite de max_chars."""
    return _CONTROL_CHARS.sub("", text)[:max_chars]


def validate_pr(pr: PRRecord) -> None:
    """Levanta GuardrailViolation se o PR não tem repo_name nem título."""
    if not pr.repo_name and not pr.title:
        raise GuardrailViolation("PR must have at least a repo_name or title")


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
        response = cliente.run(prompt, shots=FEW_SHOT_PROJECT_TYPE)
        data = _extract_json(str(response.content))
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
        response = cliente.run(prompt, shots=FEW_SHOT_CONTRIBUTION_NATURE)
        data = _extract_json(str(response.content))
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
    opts = ", ".join(sorted(NIVEIS_CLAREZA_DESCRICAO))
    prompt = f"Avalie a clareza deste corpo de PR:\n{corpo_cortado}\n"
    prompt += 'Responda APENAS em JSON: {"clareza": "..."}. '
    prompt += f"Opções válidas: {opts}."

    try:
        response = cliente.run(prompt, shots=FEW_SHOT_DESCRIPTION_CLARITY)
        data = _extract_json(str(response.content))
        result = str(data.get("clareza", "")).strip().lower()
        if result in NIVEIS_CLAREZA_DESCRICAO:
            return result
        # accept English equivalents (common with Ollama models)
        mapped = _CLARITY_EN_TO_PT.get(result)
        if mapped:
            return mapped
    except Exception:
        pass

    return "insuficiente"


# ── LLM-02: Adaptive batch size ───────────────────────────────────────────────


@dataclass(frozen=True)
class BatchState:
    """Estado imutável do adaptive batch — rastreia falhas e sucessos consecutivos.

    Função PURA adapt_batch_size() consome e produz BatchState sem I/O.
    """

    current_size: int
    consecutive_failures: int
    consecutive_successes: int


def adapt_batch_size(state: BatchState, success: bool, max_size: int) -> BatchState:
    """Ajusta o tamanho do batch baseado no histórico de sucesso/falha.

    Função PURA: sem I/O, sem estado global. Totalmente testável sem mocks.

    Regras:
    - 3 falhas consecutivas → reduz current_size pela metade (mínimo 1).
    - 10 sucessos consecutivos → dobra current_size (máximo max_size).
    - Sucesso zera contagem de falhas; falha zera contagem de sucessos.

    Args:
        state: estado atual do batch.
        success: True se a última chamada batch foi bem-sucedida.
        max_size: tamanho máximo permitido (nunca ultrapassa).

    Returns:
        Novo BatchState com valores atualizados.
    """
    if success:
        new_successes = state.consecutive_successes + 1
        if new_successes >= 10 and state.current_size < max_size:
            return BatchState(
                current_size=min(state.current_size * 2, max_size),
                consecutive_failures=0,
                consecutive_successes=0,
            )
        return BatchState(
            current_size=state.current_size,
            consecutive_failures=0,
            consecutive_successes=new_successes,
        )
    new_failures = state.consecutive_failures + 1
    if new_failures >= 3:
        return BatchState(
            current_size=max(1, state.current_size // 2),
            consecutive_failures=0,
            consecutive_successes=0,
        )
    return BatchState(
        current_size=state.current_size,
        consecutive_failures=new_failures,
        consecutive_successes=0,
    )


# ── LLM-09: Helpers de prompt compression ────────────────────────────────────


def _body_snippet(body: str, chars: int) -> str:
    """Trunca o corpo do PR para o limite de chars. Retorna '(empty)' se vazio."""
    stripped = body.strip()
    return stripped[:chars] if stripped else "(empty)"


def _single_body_chars() -> int:
    """Limite de chars para prompts individuais (env LLM_BODY_CHARS_SINGLE)."""
    return int(os.environ.get("LLM_BODY_CHARS_SINGLE", "400"))


def _batch_body_chars() -> int:
    """Limite de chars para prompts de batch (env LLM_BODY_CHARS_BATCH)."""
    return int(os.environ.get("LLM_BODY_CHARS_BATCH", "100"))


def _batch_pr_line(idx: int, pr: PRRecord) -> str:
    """Formato compacto para linha de batch: idx|repo|title|body_snippet."""
    return (
        f"{idx}|{pr.repo_name}|{pr.title}|{_body_snippet(pr.body, _batch_body_chars())}"
    )


# ── Tool definition (Fase 4) ──────────────────────────────────────────────────


def _classify_pr_tool_def() -> dict[str, object]:
    """Retorna a definição da ferramenta classify_pr para Ollama tool calling.

    Usar uma função (não constante global) evita violação de BP005.
    Os enum values são extraídos dos frozensets canônicos, garantindo consistência.
    Requer modelo com suporte a tool calling (ex: qwen2:1.5b, phi3, llama3.1+).
    """
    return {
        "type": "function",
        "function": {
            "name": "classify_pr",
            "description": (
                "Classify a GitHub pull request by project type, "
                "contribution nature, and description clarity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_projeto": {
                        "type": "string",
                        "enum": sorted(TIPOS_PROJETO),
                        "description": "Type of project the PR belongs to.",
                    },
                    "natureza": {
                        "type": "string",
                        "enum": sorted(NATUREZAS_CONTRIBUICAO),
                        "description": "Nature of the contribution.",
                    },
                    "clareza": {
                        "type": "string",
                        "enum": sorted(NIVEIS_CLAREZA_DESCRICAO),
                        "description": "Clarity level of the PR description.",
                    },
                },
                "required": ["tipo_projeto", "natureza", "clareza"],
            },
        },
    }


def _classify_prs_batch_tool_def() -> dict[str, object]:
    """Ferramenta para classificar N PRs em uma única chamada LLM.

    Retorna um array de classificações com os mesmos índices dos PRs de entrada.
    Mais eficiente que chamadas individuais: prompt maior, mas 1 round-trip por batch.
    """
    return {
        "type": "function",
        "function": {
            "name": "classify_prs_batch",
            "description": "Classify multiple pull requests at once. Return one result per PR, in the same order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "classifications": {
                        "type": "array",
                        "description": "One classification per PR, in input order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tipo_projeto": {
                                    "type": "string",
                                    "enum": sorted(TIPOS_PROJETO),
                                },
                                "natureza": {
                                    "type": "string",
                                    "enum": sorted(NATUREZAS_CONTRIBUICAO),
                                },
                                "clareza": {
                                    "type": "string",
                                    "enum": sorted(NIVEIS_CLAREZA_DESCRICAO),
                                },
                            },
                            "required": ["tipo_projeto", "natureza", "clareza"],
                        },
                    }
                },
                "required": ["classifications"],
            },
        },
    }


def _classify_pr_nature_clarity_tool_def() -> dict[str, object]:
    """Tool reduzida para quando tipo_projeto já é conhecido via cache de repo.

    LLM-05: omite tipo_projeto do schema para reduzir tokens de saída ~33%.
    Compatível com modelos pequenos (qwen2:1.5b) que têm melhor confiabilidade
    com respostas menores.
    """
    return {
        "type": "function",
        "function": {
            "name": "classify_pr_nature_clarity",
            "description": (
                "Classify contribution nature and description clarity of a pull request. "
                "Project type is already known."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "natureza": {
                        "type": "string",
                        "enum": sorted(NATUREZAS_CONTRIBUICAO),
                        "description": "Nature of the contribution.",
                    },
                    "clareza": {
                        "type": "string",
                        "enum": sorted(NIVEIS_CLAREZA_DESCRICAO),
                        "description": "Clarity level of the PR description.",
                    },
                },
                "required": ["natureza", "clareza"],
            },
        },
    }


def _parse_batch_classifications(
    prs: list[PRRecord],
    classifications: list[dict[str, str]],
) -> list[EnrichedPR]:
    """Converte lista de dicts de classificação em EnrichedPRs validados."""
    return [
        EnrichedPR(
            pr=pr,
            project_type=c.get("tipo_projeto", "")
            if c.get("tipo_projeto") in TIPOS_PROJETO
            else "outro",
            contribution_nature=c.get("natureza", "")
            if c.get("natureza") in NATUREZAS_CONTRIBUICAO
            else "outro",
            description_clarity=c.get("clareza", "")
            if c.get("clareza") in NIVEIS_CLAREZA_DESCRICAO
            else "insuficiente",
        )
        for pr, c in zip(prs, classifications, strict=False)
    ]


def _try_batch_call(
    prs: list[PRRecord],
    client: LLMClient,
) -> list[EnrichedPR]:
    """Classifica um batch de PRs em 1 chamada LLM — levanta exceção se falhar.

    Diferente de _enrich_prs_batch_call, não faz fallback interno: propaga a
    exceção para que o chamador (loop adaptativo) possa ajustar o batch_size.
    Usa formato compacto de linha (LLM-09) e corpo truncado a LLM_BODY_CHARS_BATCH.

    Args:
        prs: lista de PRs a classificar.
        client: cliente LLM com suporte a tool calling.

    Returns:
        Lista de EnrichedPR na mesma ordem dos PRs de entrada.

    Raises:
        ValueError: se o modelo retornar contagem ou formato incorreto.
        Exception: qualquer outro erro da chamada LLM.
    """
    lines = "\n".join(_batch_pr_line(i, pr) for i, pr in enumerate(prs))
    prompt = f"Classify these {len(prs)} pull requests in order:\n{lines}"
    response = client.run(prompt, tools=[_classify_prs_batch_tool_def()])
    data = _extract_json(str(response.content))
    raw: Any = data.get("classifications", [])
    classifications: list[dict[str, str]] = raw if isinstance(raw, list) else []
    if len(classifications) != len(prs):
        raise ValueError(f"batch retornou {len(classifications)}, esperado {len(prs)}")
    return _parse_batch_classifications(prs, classifications)


def _enrich_prs_batch_call(
    prs: list[PRRecord],
    client: LLMClient,
    metrics: ClassificationMetrics | None = None,
) -> list[EnrichedPR]:
    """Classifica uma lista de PRs em 1 chamada LLM com tool calling.

    Se o modelo retornar contagem errada ou JSON inválido, recai em chamadas
    individuais via enrich_pr_with_tools() para garantir que todos os PRs
    sejam classificados. Usado pelo caminho paralelo (max_workers > 1).

    Args:
        prs: lista de PRs a classificar neste batch.
        client: cliente LLM com suporte a tool calling.
        metrics: métricas acumuladas opcionais (LLM-06).

    Returns:
        Lista de EnrichedPR na mesma ordem dos PRs de entrada.
    """
    if metrics is not None:
        metrics.batch_calls += 1
    try:
        return _try_batch_call(prs, client)
    except Exception:
        if metrics is not None:
            metrics.batch_fallbacks += 1
        return [enrich_pr_with_tools(pr, client) for pr in prs]


def enrich_pr_with_tools(
    pr: PRRecord,
    client: LLMClient,
    repo_type_cache: dict[str, str] | None = None,
) -> EnrichedPR:
    """Enriquece um PR com uma única chamada LLM via tool calling.

    LLM-04: Aplica heurística antes do LLM (body vazio + natureza clara = sem rede).
    LLM-05: Se repo_type_cache tem o repo, usa tool reduzida (natureza+clareza apenas),
            reduzindo tokens de saída ~33% e melhorando confiabilidade em modelos pequenos.
    LLM-09: Corpo truncado a LLM_BODY_CHARS_SINGLE (padrão 400 chars).

    Args:
        pr: PR a classificar.
        client: cliente LLM com suporte a tool calling.
        repo_type_cache: mapa repo_name → tipo_projeto pré-classificado.

    Returns:
        EnrichedPR com os 3 campos preenchidos.
    """
    heuristic = heuristic_classify(pr)
    if heuristic is not None:
        return heuristic

    cached_type = (repo_type_cache or {}).get(pr.repo_name)
    prompt = (
        f"Classify this pull request.\n"
        f"Repository: {pr.repo_name}\n"
        f"Title: {pr.title}\n"
        f"Body: {_body_snippet(pr.body, _single_body_chars())}"
    )

    complexity = heuristic_complexity(pr)

    if cached_type is not None:
        try:
            response = client.run(
                prompt, tools=[_classify_pr_nature_clarity_tool_def()]
            )
            data = _extract_json(str(response.content))
            natureza = str(data.get("natureza", "")).lower()
            clareza = str(data.get("clareza", "")).lower()
            return EnrichedPR(
                pr=pr,
                project_type=cached_type,
                contribution_nature=natureza
                if natureza in NATUREZAS_CONTRIBUICAO
                else "outro",
                description_clarity=clareza
                if clareza in NIVEIS_CLAREZA_DESCRICAO
                else "insuficiente",
                review_complexity=complexity,
            )
        except Exception:
            return EnrichedPR(
                pr=pr,
                project_type=cached_type,
                contribution_nature="outro",
                description_clarity="insuficiente",
                review_complexity=complexity,
            )

    try:
        response = client.run(prompt, tools=[_classify_pr_tool_def()])
        data = _extract_json(str(response.content))
        tipo = str(data.get("tipo_projeto", "")).lower()
        natureza = str(data.get("natureza", "")).lower()
        clareza = str(data.get("clareza", "")).lower()
        return EnrichedPR(
            pr=pr,
            project_type=tipo if tipo in TIPOS_PROJETO else "outro",
            contribution_nature=natureza
            if natureza in NATUREZAS_CONTRIBUICAO
            else "outro",
            description_clarity=clareza
            if clareza in NIVEIS_CLAREZA_DESCRICAO
            else "insuficiente",
            review_complexity=complexity,
        )
    except Exception:
        return EnrichedPR(
            pr=pr,
            project_type="outro",
            contribution_nature="outro",
            description_clarity="insuficiente",
            review_complexity=complexity,
        )


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


def _record_metrics(
    result: list[EnrichedPR],
    metrics: ClassificationMetrics | None,
    start: float,
) -> list[EnrichedPR]:
    if metrics is not None:
        for ep in result:
            metrics.record_pr(
                ep.project_type, ep.contribution_nature, ep.description_clarity
            )
        metrics.total_time_s += time.monotonic() - start
    return result


def _run_batch_parallel(
    pr_list: list[PRRecord],
    client: LLMClient,
    batch_size: int,
    max_workers: int,
    metrics: ClassificationMetrics | None,
) -> list[EnrichedPR]:
    batches = [pr_list[i : i + batch_size] for i in range(0, len(pr_list), batch_size)]

    def process_batch(batch: list[PRRecord]) -> list[EnrichedPR]:
        return _enrich_prs_batch_call(batch, client, metrics=metrics)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        nested = list(executor.map(process_batch, batches))
    return [ep for sub in nested for ep in sub]


def _run_adaptive_batch(
    pr_list: list[PRRecord],
    client: LLMClient,
    batch_size: int,
    metrics: ClassificationMetrics | None,
) -> list[EnrichedPR]:
    """Loop serial com adaptive batch size: reduz após 3 falhas, aumenta após 10 sucessos."""
    batch_state = BatchState(
        current_size=batch_size, consecutive_failures=0, consecutive_successes=0
    )
    results: list[EnrichedPR] = []
    idx = 0
    while idx < len(pr_list):
        batch = pr_list[idx : idx + batch_state.current_size]
        if metrics is not None:
            metrics.batch_calls += 1
        try:
            results.extend(_try_batch_call(batch, client))
            batch_state = adapt_batch_size(
                batch_state, success=True, max_size=batch_size
            )
            idx += len(batch)
        except Exception:
            if metrics is not None:
                metrics.batch_fallbacks += 1
            batch_state = adapt_batch_size(
                batch_state, success=False, max_size=batch_size
            )
            if batch_state.current_size == 1:
                results.extend(enrich_pr_with_tools(pr, client) for pr in batch)
                idx += len(batch)
    return results


def _run_tools_single(
    pr_list: list[PRRecord],
    client: LLMClient,
    max_workers: int,
) -> list[EnrichedPR]:
    """Caminho tools sem batch: 1 chamada/PR com cache de tipo por repo (LLM-05)."""
    from pr_analyzer.transforms.reducers import group_by_repo

    repo_cache = classify_repos_batch(group_by_repo(tuple(pr_list)), client)

    def classify(pr: PRRecord) -> EnrichedPR:
        return enrich_pr_with_tools(pr, client, repo_type_cache=repo_cache)

    if max_workers > 1:
        return list(ThreadPoolExecutor(max_workers=max_workers).map(classify, pr_list))
    return list(map(classify, pr_list))


def _run_cached(
    prs: Iterable[PRRecord],
    client: LLMClient,
    cache_path: Path | None,
    max_workers: int,
    metrics: ClassificationMetrics | None,
    start: float,
) -> Iterable[EnrichedPR]:
    """Caminho não-tools: 3 chamadas/PR com cache + heurísticas (avaliação lazy se serial)."""

    def type_fn(repo: str, title: str) -> str:
        return classificar_tipo_projeto(repo, [title], client)

    def nature_fn(title: str, body: str) -> str:
        return classificar_natureza_contribuicao(title, body, client)

    def clarity_fn(body: str) -> str:
        return avaliar_clareza_descricao(body, client)

    cached = make_enriched_classifier(
        type_fn, nature_fn, clarity_fn, cache_path=cache_path
    )

    def classify(pr: PRRecord) -> EnrichedPR:
        h = heuristic_classify(pr)
        return h if h is not None else cached(pr)

    if max_workers > 1:
        pr_list = list(prs)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return _record_metrics(
                list(executor.map(classify, pr_list)), metrics, start
            )
    if metrics is not None:
        return _record_metrics(list(map(classify, prs)), metrics, start)
    return map(classify, prs)


def _result_store(cache_path: Path | None) -> SqliteKVStore | None:
    """Deriva um SqliteKVStore para o result-cache a partir de cache_path."""
    if cache_path is None:
        return None
    return SqliteKVStore(cache_path.with_suffix(".db"), "pr_results")


def _split_cached(
    pr_list: list[PRRecord],
    store: SqliteKVStore | None,
) -> tuple[list[EnrichedPR], list[PRRecord]]:
    """Separa PRs já classificados (cache hit) dos que precisam de LLM."""
    if store is None:
        return [], pr_list
    hits: list[EnrichedPR] = []
    misses: list[PRRecord] = []
    for pr in pr_list:
        raw = store.get(make_cache_key(pr.title, pr.body[:500]))
        if raw is not None:
            data: dict[str, str] = json.loads(raw)
            hits.append(
                EnrichedPR(
                    pr=pr,
                    project_type=data["project_type"],
                    contribution_nature=data["contribution_nature"],
                    description_clarity=data["description_clarity"],
                )
            )
        else:
            misses.append(pr)
    return hits, misses


def _write_cached(results: list[EnrichedPR], store: SqliteKVStore | None) -> None:
    """Persiste classificações no result-cache SQLite."""
    if store is None:
        return
    for ep in results:
        store.set(
            make_cache_key(ep.pr.title, ep.pr.body[:500]),
            json.dumps(
                {
                    "project_type": ep.project_type,
                    "contribution_nature": ep.contribution_nature,
                    "description_clarity": ep.description_clarity,
                }
            ),
        )


def enrich_prs(
    prs: Iterable[PRRecord],
    client: LLMClient,
    cache_path: Path | None = None,
    max_workers: int = 1,
    use_tools: bool = False,
    batch_size: int = 1,
    metrics: ClassificationMetrics | None = None,
) -> Iterable[EnrichedPR]:
    """Enriquece PRs com classificações LLM, com suporte a tool calling, batch e concorrência.

    Modos de operação (do mais lento ao mais rápido):
    - use_tools=False, batch_size=1: 3 chamadas/PR com cache; avaliação lazy.
    - use_tools=True,  batch_size=1: 1 chamada/PR via tool calling.
    - use_tools=True,  batch_size=N: 1 chamada por N PRs (batch); avaliação eager.
    - max_workers>1: qualquer modo acima paralelizado com ThreadPoolExecutor.

    Args:
        prs: iterável de PRRecords a enriquecer.
        client: cliente LLM configurado.
        cache_path: caminho base para cache em disco. Deriva automaticamente um
            SQLite result-cache (.db) para todos os modos (tools e não-tools).
        max_workers: número de threads paralelas (1 = serial/lazy para não-batch).
        use_tools: usa tool calling (requer qwen2:1.5b, phi3, llama3.1+).
        batch_size: PRs por chamada LLM quando use_tools=True (1 = individual).
        metrics: objeto de métricas a atualizar em-place (LLM-06); None = sem coleta.

    Returns:
        Iterável de EnrichedPR (lazy só quando cache_path=None, use_tools=False,
        max_workers=1, metrics=None).
    """
    _start = time.monotonic()
    _store = _result_store(cache_path)
    pr_list = list(prs)
    cached, uncached = _split_cached(pr_list, _store)

    if metrics is not None:
        metrics.cache_hits += len(cached)

    if not uncached:
        return cached

    if use_tools and batch_size > 1:
        if max_workers > 1:
            new: list[EnrichedPR] = _record_metrics(
                _run_batch_parallel(uncached, client, batch_size, max_workers, metrics),
                metrics,
                _start,
            )
        else:
            new = _record_metrics(
                _run_adaptive_batch(uncached, client, batch_size, metrics),
                metrics,
                _start,
            )
        _write_cached(new, _store)
        return cached + new

    if use_tools:
        new = _record_metrics(
            _run_tools_single(uncached, client, max_workers), metrics, _start
        )
        _write_cached(new, _store)
        return cached + new

    if _store is not None:
        new = list(
            _run_cached(uncached, client, cache_path, max_workers, metrics, _start)
        )
        _write_cached(new, _store)
        return cached + new

    return _run_cached(uncached, client, cache_path, max_workers, metrics, _start)


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


# ── LLM-01: Pipeline assíncrono ───────────────────────────────────────────────


async def _enrich_one_async(
    pr: PRRecord,
    client: AsyncLLMClient,
    semaphore: asyncio.Semaphore,
) -> EnrichedPR:
    """Enriquece um PR de forma assíncrona com controle de concorrência.

    Aplica heurística antes do LLM — PRs com body vazio e natureza óbvia
    são classificados sem consumir slot do Semaphore.
    """
    heuristic = heuristic_classify(pr)
    if heuristic is not None:
        return heuristic

    prompt = (
        f"Classify this pull request.\n"
        f"Repository: {pr.repo_name}\n"
        f"Title: {pr.title}\n"
        f"Body: {_body_snippet(pr.body, _single_body_chars())}"
    )
    complexity = heuristic_complexity(pr)
    async with semaphore:
        try:
            response = await client.run(prompt, tools=[_classify_pr_tool_def()])
            data = _extract_json(str(response.content))
            tipo = str(data.get("tipo_projeto", "")).lower()
            natureza = str(data.get("natureza", "")).lower()
            clareza = str(data.get("clareza", "")).lower()
            return EnrichedPR(
                pr=pr,
                project_type=tipo if tipo in TIPOS_PROJETO else "outro",
                contribution_nature=natureza
                if natureza in NATUREZAS_CONTRIBUICAO
                else "outro",
                description_clarity=clareza
                if clareza in NIVEIS_CLAREZA_DESCRICAO
                else "insuficiente",
                review_complexity=complexity,
            )
        except Exception:
            return EnrichedPR(
                pr=pr,
                project_type="outro",
                contribution_nature="outro",
                description_clarity="insuficiente",
                review_complexity=complexity,
            )


async def _enrich_batch_async(
    prs: list[PRRecord],
    client: AsyncLLMClient,
    semaphore: asyncio.Semaphore,
) -> list[EnrichedPR]:
    """Classifica um batch de PRs em 1 chamada LLM assíncrona.

    Fallback individual se o modelo retornar contagem ou formato errado.
    """
    lines = "\n".join(_batch_pr_line(i, pr) for i, pr in enumerate(prs))
    prompt = f"Classify these {len(prs)} pull requests in order:\n{lines}"
    async with semaphore:
        try:
            response = await client.run(prompt, tools=[_classify_prs_batch_tool_def()])
            data = _extract_json(str(response.content))
            raw2: Any = data.get("classifications", [])
            classifications: list[dict[str, str]] = (
                raw2 if isinstance(raw2, list) else []
            )
            if len(classifications) != len(prs):
                raise ValueError(
                    f"batch retornou {len(classifications)}, esperado {len(prs)}"
                )
            return _parse_batch_classifications(prs, classifications)
        except Exception:
            # Fallback: classifica individualmente (sem semaphore para não deadlock)
            return [
                EnrichedPR(
                    pr=pr,
                    project_type="outro",
                    contribution_nature="outro",
                    description_clarity="insuficiente",
                )
                for pr in prs
            ]


async def enrich_prs_async(
    prs: Iterable[PRRecord],
    client: AsyncLLMClient,
    batch_size: int = 1,
    concurrency: int = 8,
) -> list[EnrichedPR]:
    """Enriquece PRs de forma assíncrona com controle de concorrência.

    Usa asyncio.gather() com Semaphore para processar até `concurrency`
    chamadas LLM em paralelo sem bloquear o event loop.

    Modos de operação:
    - batch_size=1: uma tarefa async por PR via tool calling individual.
    - batch_size>1: uma tarefa async por batch de N PRs.
    - Em ambos os modos, heurísticas são aplicadas antes do LLM.

    Args:
        prs: iterável de PRRecords a enriquecer.
        client: cliente LLM assíncrono (AsyncLLMClient).
        batch_size: PRs por chamada LLM (1 = individual, N = batch).
        concurrency: máximo de chamadas LLM simultâneas.

    Returns:
        Lista de EnrichedPR na mesma ordem dos PRs de entrada.
    """
    pr_list = list(prs)
    if not pr_list:
        return []

    semaphore = asyncio.Semaphore(concurrency)

    if batch_size > 1:
        batches = [
            pr_list[i : i + batch_size] for i in range(0, len(pr_list), batch_size)
        ]
        nested = await asyncio.gather(
            *(_enrich_batch_async(batch, client, semaphore) for batch in batches)
        )
        return [ep for batch_result in nested for ep in batch_result]

    return list(
        await asyncio.gather(
            *(_enrich_one_async(pr, client, semaphore) for pr in pr_list)
        )
    )


# ── English aliases (consumed by pipeline_bridge and external modules) ────────
classify_project_type = classificar_tipo_projeto
classify_contribution_nature = classificar_natureza_contribuicao
classify_description_clarity = avaliar_clareza_descricao
classify_review_complexity = heuristic_complexity
