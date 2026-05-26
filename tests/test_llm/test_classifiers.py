"""Testes para src/pr_analyzer/llm/classifiers.py — TASK-09, TASK-34, TASK-35."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv

from pr_analyzer.io.csv_reader import PRRecord
from pr_analyzer.llm.classifiers import (
    NATUREZAS_CONTRIBUICAO,
    NIVEIS_CLAREZA_DESCRICAO,
    TIPOS_PROJETO,
    avaliar_clareza_descricao,
    classificar_natureza_contribuicao,
    classificar_tipo_projeto,
    classify_repos_batch,
    enrich_pr_with_tools,
    enrich_prs,
    safe_classify,
)
from pr_analyzer.llm.client import create_groq_client
from pr_analyzer.pipeline.builder import EnrichedPR


@pytest.fixture()  # type: ignore[misc]
def mock_client() -> MagicMock:
    return MagicMock()


# ── frozensets ────────────────────────────────────────────────────────────────


def test_tipos_projeto_é_frozenset() -> None:
    assert isinstance(TIPOS_PROJETO, frozenset)


def test_naturezas_contribuicao_é_frozenset() -> None:
    assert isinstance(NATUREZAS_CONTRIBUICAO, frozenset)


def test_niveis_clareza_descricao_é_frozenset() -> None:
    assert isinstance(NIVEIS_CLAREZA_DESCRICAO, frozenset)


def test_tipos_projeto_nao_esta_vazio() -> None:
    assert len(TIPOS_PROJETO) > 0


def test_naturezas_contribuicao_nao_esta_vazio() -> None:
    assert len(NATUREZAS_CONTRIBUICAO) > 0


def test_niveis_clareza_descricao_nao_esta_vazio() -> None:
    assert len(NIVEIS_CLAREZA_DESCRICAO) > 0


# ── classificar_tipo_projeto ─────────────────────────────────────────────────────


def test_classificar_tipo_projeto_parse_json(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = '{"tipo_projeto": "biblioteca"}'
    result = classificar_tipo_projeto("repo", ["title"], mock_client)
    assert result == "biblioteca"
    # Garantir que a palavra JSON está no prompt
    assert "JSON" in mock_client.run.call_args[0][0].upper()


def test_classificar_tipo_projeto_fallback_invalid_json(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = "invalid json"
    result = classificar_tipo_projeto("repo", ["title"], mock_client)
    assert result == "outro"


def test_classificar_tipo_projeto_fallback_invalid_value(
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = '{"tipo_projeto": "valor_invalido"}'
    result = classificar_tipo_projeto("repo", ["title"], mock_client)
    assert result == "outro"


@pytest.mark.integration()
def test_classificar_tipo_projeto_integration() -> None:
    load_dotenv()
    if "GROQ_API_KEY" not in os.environ:
        pytest.skip("Requer GROQ_API_KEY no .env")
    client = create_groq_client()
    result = classificar_tipo_projeto(
        "django/django", ["fix admin bug", "add feature"], client
    )
    assert result in TIPOS_PROJETO


# ── classificar_natureza_contribuicao ──────────────────────────────────────────────


def test_classificar_natureza_contribuicao_parse_json(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = '{"natureza": "bug fix"}'
    result = classificar_natureza_contribuicao(
        "Fix memory leak", "Body content", mock_client
    )
    assert result == "bug fix"
    prompt = mock_client.run.call_args[0][0]
    assert "JSON" in prompt.upper()


def test_classificar_natureza_contribuicao_truncates_body_to_300(
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = '{"natureza": "outro"}'
    long_body = "A" * 500
    classificar_natureza_contribuicao("title", long_body, mock_client)
    prompt = mock_client.run.call_args[0][0]
    assert len(long_body) > 300
    assert "A" * 300 in prompt
    assert "A" * 301 not in prompt


def test_classificar_natureza_contribuicao_fallback_invalid_json(
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = "invalid"
    result = classificar_natureza_contribuicao("title", "body", mock_client)
    assert result == "outro"


def test_classificar_natureza_contribuicao_fallback_invalid_value(
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = '{"natureza": "invalido"}'
    result = classificar_natureza_contribuicao("title", "body", mock_client)
    assert result == "outro"


# ── avaliar_clareza_descricao ──────────────────────────────────────────────


def test_avaliar_clareza_descricao_short_circuit_empty(mock_client: MagicMock) -> None:
    result = avaliar_clareza_descricao("   \n", mock_client)
    assert result == "insuficiente"
    mock_client.run.assert_not_called()


def test_avaliar_clareza_descricao_truncates_body_to_500(
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = "boa"
    long_body = "B" * 600
    avaliar_clareza_descricao(long_body, mock_client)
    prompt = mock_client.run.call_args[0][0]
    assert "B" * 500 in prompt
    assert "B" * 501 not in prompt


def test_avaliar_clareza_descricao_valid_return(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = '{"clareza": "excelente"}'
    result = avaliar_clareza_descricao("Good body", mock_client)
    assert result == "excelente"


def test_avaliar_clareza_descricao_fallback_invalid(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = "muito bom (invalido)"
    result = avaliar_clareza_descricao("Good body", mock_client)
    assert result == "insuficiente"


# ── classify_repos_batch (TASK-34) ────────────────────────────────────────────


def test_classify_repos_batch_vazio(mock_client: MagicMock) -> None:
    result = classify_repos_batch({}, mock_client)
    assert result == {}
    mock_client.run.assert_not_called()


def test_classify_repos_batch_um_repo_uma_chamada_llm(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value.content = '{"tipo_projeto": "biblioteca"}'
    groups: dict[str, list[PRRecord]] = {"org/repo": [sample_pr] * 10}
    classify_repos_batch(groups, mock_client)
    assert mock_client.run.call_count == 1


def test_classify_repos_batch_dois_repos_duas_chamadas(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value.content = '{"tipo_projeto": "framework"}'
    groups: dict[str, list[PRRecord]] = {
        "org/repo1": [sample_pr],
        "org/repo2": [sample_pr._replace(repo_name="org/repo2")],
    }
    classify_repos_batch(groups, mock_client)
    assert mock_client.run.call_count == 2


def test_classify_repos_batch_retorna_dict_str_str(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value.content = '{"tipo_projeto": "ferramenta"}'
    result = classify_repos_batch({"org/repo": [sample_pr]}, mock_client)
    assert isinstance(result, dict)
    assert result["org/repo"] == "ferramenta"


def test_classify_repos_batch_fallback_json_invalido(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value.content = "não é json"
    result = classify_repos_batch({"org/repo": [sample_pr]}, mock_client)
    assert result["org/repo"] == "outro"


def test_classify_repos_batch_inclui_titulos_no_prompt(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value.content = '{"tipo_projeto": "aplicação web"}'
    classify_repos_batch({"org/repo": [sample_pr]}, mock_client)
    prompt = mock_client.run.call_args[0][0]
    assert sample_pr.title in prompt


# ── enrich_prs (TASK-35) ──────────────────────────────────────────────────────


def test_enrich_prs_retorna_iteravel(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    result = enrich_prs([sample_pr], mock_client)
    assert hasattr(result, "__iter__")
    assert not isinstance(result, list | tuple)


def test_enrich_prs_e_lazy(mock_client: MagicMock, sample_pr: PRRecord) -> None:
    enrich_prs(iter([sample_pr, sample_pr]), mock_client)
    mock_client.run.assert_not_called()


def test_enrich_prs_produz_enriched_pr(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.side_effect = [
        MagicMock(content='{"tipo_projeto": "biblioteca"}'),
        MagicMock(content='{"natureza": "bug fix"}'),
        MagicMock(content="boa"),
    ]
    result = list(enrich_prs([sample_pr], mock_client))
    assert len(result) == 1
    assert isinstance(result[0], EnrichedPR)
    assert result[0].pr == sample_pr


def test_enrich_prs_aplica_tres_classificadores(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.side_effect = [
        MagicMock(content='{"tipo_projeto": "framework"}'),
        MagicMock(content='{"natureza": "feature"}'),
        MagicMock(content='{"clareza": "excelente"}'),
    ]
    result = list(enrich_prs([sample_pr], mock_client))
    assert result[0].project_type == "framework"
    assert result[0].contribution_nature == "feature"
    assert result[0].description_clarity == "excelente"


def test_enrich_prs_body_vazio_retorna_insuficiente_sem_chamar_llm(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    # sample_pr.title = "Fix memory leak in parser" — sem "fix" nos _BUG_KEYWORDS,
    # mas "bug" e "crash" estão. Precisamos de um título que a heurística
    # não cubra (ambíguo) para testar que clareza=insuficiente vem do LLM.
    pr_sem_body = sample_pr._replace(title="Update configuration", body="")
    mock_client.run.side_effect = [
        MagicMock(content='{"tipo_projeto": "biblioteca"}'),
        MagicMock(content='{"natureza": "outro"}'),
    ]
    result = list(enrich_prs([pr_sem_body], mock_client))
    assert result[0].description_clarity == "insuficiente"
    assert mock_client.run.call_count == 2


def test_enrich_prs_cache_persiste_entre_chamadas(
    mock_client: MagicMock, sample_pr: PRRecord, tmp_path: Path
) -> None:
    cache_file = tmp_path / "enrich.json"
    mock_client.run.side_effect = [
        MagicMock(content='{"tipo_projeto": "biblioteca"}'),
        MagicMock(content='{"natureza": "bug fix"}'),
        MagicMock(content='{"clareza": "boa"}'),
    ]
    list(enrich_prs([sample_pr], mock_client, cache_path=cache_file))

    mock_client.run.reset_mock()
    list(enrich_prs([sample_pr], mock_client, cache_path=cache_file))
    assert mock_client.run.call_count == 0


# ── TASK-45 — Testes de contrato dos classificadores ─────────────────────────
# Invariante: o output SEMPRE pertence ao frozenset válido, independente do
# input ou da resposta do LLM (inclusive inputs extremos e respostas inválidas).


@pytest.mark.parametrize(
    ("nome_repo", "titulos"),
    [
        ("org/repo", ["Fix bug"]),
        ("org/repo", [""]),
        ("org/repo", ["A" * 10_000]),
        ("org/repo", ["título ç €uro 🔥 \x00 \n\t"]),
        ("", ["title"]),
    ],
)
@pytest.mark.parametrize(
    "llm_content",
    [
        '{"tipo_projeto": "biblioteca"}',
        '{"tipo_projeto": "valor_invalido"}',
        "garbage não-json",
        "",
    ],
)
def test_tipo_projeto_contrato_output_sempre_valido(
    nome_repo: str,
    titulos: list[str],
    llm_content: str,
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = llm_content
    result = classificar_tipo_projeto(nome_repo, titulos, mock_client)
    assert result in TIPOS_PROJETO


def test_tipo_projeto_contrato_excecao_de_rede(mock_client: MagicMock) -> None:
    mock_client.run.side_effect = ConnectionError("network fail")
    result = classificar_tipo_projeto("org/repo", ["title"], mock_client)
    assert result in TIPOS_PROJETO


@pytest.mark.parametrize(
    ("titulo", "corpo"),
    [
        ("Fix bug", "Some body"),
        ("", "Some body"),
        ("Fix bug", ""),
        ("Fix bug", "B" * 10_000),
        ("título ç 🔥", "corpo €special \x00 \n\t"),
    ],
)
@pytest.mark.parametrize(
    "llm_content",
    [
        '{"natureza": "bug fix"}',
        '{"natureza": "invalido"}',
        "garbage não-json",
        "",
    ],
)
def test_natureza_contribuicao_contrato_output_sempre_valido(
    titulo: str,
    corpo: str,
    llm_content: str,
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = llm_content
    result = classificar_natureza_contribuicao(titulo, corpo, mock_client)
    assert result in NATUREZAS_CONTRIBUICAO


def test_natureza_contribuicao_contrato_excecao_de_rede(
    mock_client: MagicMock,
) -> None:
    mock_client.run.side_effect = ConnectionError("network fail")
    result = classificar_natureza_contribuicao("title", "body", mock_client)
    assert result in NATUREZAS_CONTRIBUICAO


@pytest.mark.parametrize(
    "corpo",
    [
        "Normal body",
        "",
        "   \n\t  ",
        "C" * 10_000,
        "clareza €special ç 🔥 \x00 \n\t",
    ],
)
@pytest.mark.parametrize(
    "llm_content",
    [
        "boa",
        "excelente",
        "valor_invalido",
        "",
    ],
)
def test_clareza_descricao_contrato_output_sempre_valido(
    corpo: str,
    llm_content: str,
    mock_client: MagicMock,
) -> None:
    mock_client.run.return_value.content = llm_content
    result = avaliar_clareza_descricao(corpo, mock_client)
    assert result in NIVEIS_CLAREZA_DESCRICAO


def test_clareza_descricao_contrato_excecao_de_rede(mock_client: MagicMock) -> None:
    mock_client.run.side_effect = ConnectionError("network fail")
    result = avaliar_clareza_descricao("body content", mock_client)
    assert result in NIVEIS_CLAREZA_DESCRICAO


# ── TASK-44 — safe_classify() HOF ────────────────────────────────────────────
# TDD: testes escritos antes da implementação.


def test_safe_classify_retorna_callable() -> None:
    wrapped = safe_classify(lambda: "biblioteca", "outro", TIPOS_PROJETO)
    assert callable(wrapped)


def test_safe_classify_passa_resultado_valido() -> None:
    fn: MagicMock = MagicMock(return_value="biblioteca")
    wrapped = safe_classify(fn, "outro", TIPOS_PROJETO)
    assert wrapped("repo", "title") == "biblioteca"


def test_safe_classify_fallback_em_valor_invalido() -> None:
    fn: MagicMock = MagicMock(return_value="valor_fora_do_conjunto")
    wrapped = safe_classify(fn, "outro", TIPOS_PROJETO)
    assert wrapped("repo", "title") == "outro"


def test_safe_classify_fallback_em_excecao_de_rede() -> None:
    fn: MagicMock = MagicMock(side_effect=ConnectionError("network fail"))
    wrapped = safe_classify(fn, "outro", TIPOS_PROJETO)
    assert wrapped("repo", "title") == "outro"


def test_safe_classify_fallback_em_qualquer_excecao() -> None:
    fn: MagicMock = MagicMock(side_effect=ValueError("bad value"))
    wrapped = safe_classify(fn, "insuficiente", NIVEIS_CLAREZA_DESCRICAO)
    assert wrapped("body") == "insuficiente"


def test_safe_classify_sem_valid_values_passa_qualquer_string() -> None:
    fn: MagicMock = MagicMock(return_value="qualquer_coisa")
    wrapped = safe_classify(fn, "outro")
    assert wrapped() == "qualquer_coisa"


def test_safe_classify_sem_valid_values_ainda_captura_excecao() -> None:
    fn: MagicMock = MagicMock(side_effect=RuntimeError("boom"))
    wrapped = safe_classify(fn, "fallback_value")
    assert wrapped() == "fallback_value"


def test_safe_classify_fallback_deve_pertencer_ao_valid_values() -> None:
    """O fallback passado deve ser compatível com o frozenset — verificação documental."""
    fallback = "outro"
    assert fallback in TIPOS_PROJETO


# ── enrich_pr_with_tools (1 chamada LLM por PR) ───────────────────────────────


def _tool_response(tipo: str, natureza: str, clareza: str) -> MagicMock:
    import json

    mock = MagicMock()
    mock.content = json.dumps(
        {"tipo_projeto": tipo, "natureza": natureza, "clareza": clareza}
    )
    return mock


def test_enrich_pr_with_tools_retorna_enriched_pr(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")
    result = enrich_pr_with_tools(sample_pr, mock_client)
    assert isinstance(result, EnrichedPR)
    assert result.pr == sample_pr


def test_enrich_pr_with_tools_usa_uma_chamada_llm(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _tool_response("framework", "feature", "excelente")
    enrich_pr_with_tools(sample_pr, mock_client)
    assert mock_client.run.call_count == 1


def test_enrich_pr_with_tools_extrai_valores_corretos(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _tool_response(
        "ferramenta", "refatoração", "excelente"
    )
    result = enrich_pr_with_tools(sample_pr, mock_client)
    assert result.project_type == "ferramenta"
    assert result.contribution_nature == "refatoração"
    assert result.description_clarity == "excelente"


def test_enrich_pr_with_tools_fallback_valores_invalidos(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = MagicMock(
        content='{"tipo_projeto": "invalido", "natureza": "invalido", "clareza": "invalido"}'
    )
    result = enrich_pr_with_tools(sample_pr, mock_client)
    assert result.project_type in TIPOS_PROJETO
    assert result.contribution_nature in NATUREZAS_CONTRIBUICAO
    assert result.description_clarity in NIVEIS_CLAREZA_DESCRICAO


def test_enrich_pr_with_tools_fallback_json_invalido(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = MagicMock(content="not json at all")
    result = enrich_pr_with_tools(sample_pr, mock_client)
    assert result.project_type in TIPOS_PROJETO
    assert result.contribution_nature in NATUREZAS_CONTRIBUICAO
    assert result.description_clarity in NIVEIS_CLAREZA_DESCRICAO


def test_enrich_pr_with_tools_passa_tools_para_cliente(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")
    enrich_pr_with_tools(sample_pr, mock_client)
    kwargs = mock_client.run.call_args[1]
    assert "tools" in kwargs
    assert isinstance(kwargs["tools"], list)
    assert len(kwargs["tools"]) == 1


# ── enrich_prs com max_workers e use_tools ────────────────────────────────────


def test_enrich_prs_padrao_ainda_e_lazy(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    enrich_prs(iter([sample_pr]), mock_client)
    mock_client.run.assert_not_called()


def test_enrich_prs_max_workers_maior_que_1_e_eager(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")
    enrich_prs([sample_pr, sample_pr], mock_client, use_tools=True, max_workers=2)
    # LLM-05: 1 chamada para classify_repos_batch + 2 individuais = 3
    assert mock_client.run.call_count == 3


def test_enrich_prs_use_tools_usa_uma_chamada_por_pr(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _tool_response("framework", "feature", "excelente")
    result = list(enrich_prs([sample_pr, sample_pr], mock_client, use_tools=True))
    # LLM-05: 1 chamada para classify_repos_batch + 2 individuais = 3
    assert mock_client.run.call_count == 3
    assert all(isinstance(ep, EnrichedPR) for ep in result)


def test_enrich_prs_use_tools_false_usa_tres_chamadas_por_pr(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.side_effect = [
        MagicMock(content='{"tipo_projeto": "biblioteca"}'),
        MagicMock(content='{"natureza": "bug fix"}'),
        MagicMock(content='{"clareza": "boa"}'),
    ]
    list(enrich_prs([sample_pr], mock_client, use_tools=False))
    assert mock_client.run.call_count == 3


# ── batch: N PRs por chamada ──────────────────────────────────────────────────


def _batch_response(items: list[tuple[str, str, str]]) -> MagicMock:
    """Mock de resposta para classify_prs_batch com N classificações."""
    classifications = [
        {"tipo_projeto": t, "natureza": n, "clareza": c} for t, n, c in items
    ]
    mock = MagicMock()
    mock.content = json.dumps({"classifications": classifications})
    return mock


def test_enrich_prs_batch_size_usa_uma_chamada_para_n_prs(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _batch_response(
        [("biblioteca", "bug fix", "boa"), ("framework", "feature", "excelente")]
    )
    result = list(
        enrich_prs([sample_pr, sample_pr], mock_client, use_tools=True, batch_size=5)
    )
    assert mock_client.run.call_count == 1
    assert len(result) == 2


def test_enrich_prs_batch_retorna_enriched_prs_corretos(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    mock_client.run.return_value = _batch_response(
        [("ferramenta", "refatoração", "excelente")]
    )
    result = list(enrich_prs([sample_pr], mock_client, use_tools=True, batch_size=5))
    assert result[0].project_type == "ferramenta"
    assert result[0].contribution_nature == "refatoração"
    assert result[0].description_clarity == "excelente"


def test_enrich_prs_batch_agrupa_por_batch_size(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """5 PRs com batch_size=2 geram 3 chamadas (batches de 2, 2, 1)."""
    mock_client.run.side_effect = [
        _batch_response(
            [("biblioteca", "bug fix", "boa"), ("biblioteca", "bug fix", "boa")]
        ),
        _batch_response(
            [("biblioteca", "bug fix", "boa"), ("biblioteca", "bug fix", "boa")]
        ),
        _batch_response([("biblioteca", "bug fix", "boa")]),
    ]
    result = list(
        enrich_prs([sample_pr] * 5, mock_client, use_tools=True, batch_size=2)
    )
    assert mock_client.run.call_count == 3
    assert len(result) == 5


def test_enrich_prs_batch_fallback_se_contagem_errada(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """Quando o modelo retorna menos resultados que PRs no batch, cai em chamadas individuais."""
    mock_client.run.side_effect = [
        _batch_response([("biblioteca", "bug fix", "boa")]),  # batch falhou: só 1 de 3
        _tool_response("framework", "feature", "boa"),
        _tool_response("ferramenta", "bug fix", "básica"),
        _tool_response("outro", "outro", "insuficiente"),
    ]
    result = list(
        enrich_prs([sample_pr] * 3, mock_client, use_tools=True, batch_size=5)
    )
    assert len(result) == 3
    assert all(isinstance(ep, EnrichedPR) for ep in result)


def test_enrich_prs_batch_fallback_json_invalido(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """Quando o batch retorna JSON inválido, cai em chamadas individuais."""
    mock_client.run.side_effect = [
        MagicMock(content="not json"),
        _tool_response("biblioteca", "bug fix", "boa"),
        _tool_response("framework", "feature", "excelente"),
    ]
    result = list(
        enrich_prs([sample_pr] * 2, mock_client, use_tools=True, batch_size=5)
    )
    assert len(result) == 2
    assert all(r.project_type in TIPOS_PROJETO for r in result)


def test_enrich_prs_batch_passa_tools_no_formato_batch(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """Verifica que o batch usa classify_prs_batch (não classify_pr)."""
    mock_client.run.return_value = _batch_response([("biblioteca", "bug fix", "boa")])
    list(enrich_prs([sample_pr], mock_client, use_tools=True, batch_size=5))
    kwargs = mock_client.run.call_args[1]
    tool_name = kwargs["tools"][0]["function"]["name"]
    assert tool_name == "classify_prs_batch"


def test_enrich_prs_batch_size_1_usa_enrich_individual(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """batch_size=1 usa enrich_pr_with_tools (ferramenta individual, não batch)."""
    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")
    list(enrich_prs([sample_pr, sample_pr], mock_client, use_tools=True, batch_size=1))
    # Filtra apenas as chamadas com tools (a chamada de pré-classificação de repo usa shots)
    kwargs_list = [
        call[1] for call in mock_client.run.call_args_list if "tools" in call[1]
    ]
    tool_names = [kw["tools"][0]["function"]["name"] for kw in kwargs_list]
    assert all(name != "classify_prs_batch" for name in tool_names)


# ── LLM-02: BatchState e adapt_batch_size ────────────────────────────────────


def test_batch_state_e_frozen_dataclass() -> None:
    import dataclasses

    from pr_analyzer.llm.classifiers import BatchState

    state = BatchState(current_size=5, consecutive_failures=0, consecutive_successes=0)
    assert dataclasses.is_dataclass(state)
    with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
        state.current_size = 99  # type: ignore[misc]


def test_adapt_batch_size_sucesso_acumula_consecutivos() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=5, consecutive_failures=0, consecutive_successes=3)
    new = adapt_batch_size(state, success=True, max_size=10)
    assert new.current_size == 5
    assert new.consecutive_successes == 4
    assert new.consecutive_failures == 0


def test_adapt_batch_size_falha_acumula_consecutivos() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=5, consecutive_failures=1, consecutive_successes=0)
    new = adapt_batch_size(state, success=False, max_size=10)
    assert new.current_size == 5
    assert new.consecutive_failures == 2


def test_adapt_batch_size_reduz_apos_3_falhas() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=8, consecutive_failures=2, consecutive_successes=0)
    new = adapt_batch_size(state, success=False, max_size=10)
    assert new.current_size == 4
    assert new.consecutive_failures == 0


def test_adapt_batch_size_nao_cai_abaixo_de_1() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=1, consecutive_failures=2, consecutive_successes=0)
    new = adapt_batch_size(state, success=False, max_size=10)
    assert new.current_size == 1


def test_adapt_batch_size_aumenta_apos_10_sucessos() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=3, consecutive_failures=0, consecutive_successes=9)
    new = adapt_batch_size(state, success=True, max_size=10)
    assert new.current_size == 6
    assert new.consecutive_successes == 0


def test_adapt_batch_size_nao_ultrapassa_max_size() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=7, consecutive_failures=0, consecutive_successes=9)
    new = adapt_batch_size(state, success=True, max_size=10)
    assert new.current_size <= 10


def test_adapt_batch_size_sucesso_zera_falhas_consecutivas() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=5, consecutive_failures=2, consecutive_successes=0)
    new = adapt_batch_size(state, success=True, max_size=10)
    assert new.consecutive_failures == 0


def test_adapt_batch_size_falha_zera_sucessos_consecutivos() -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=5, consecutive_failures=0, consecutive_successes=5)
    new = adapt_batch_size(state, success=False, max_size=10)
    assert new.consecutive_successes == 0


def test_adapt_batch_size_e_funcao_pura_mesmo_estado() -> None:
    """adapt_batch_size não muta o estado original."""
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(current_size=5, consecutive_failures=0, consecutive_successes=0)
    adapt_batch_size(state, success=True, max_size=10)
    assert state.current_size == 5  # imutável


@pytest.mark.parametrize("initial_size", [1, 2, 4, 8, 10])
@pytest.mark.parametrize("success", [True, False])
def test_adapt_batch_size_nunca_retorna_zero(initial_size: int, success: bool) -> None:
    from pr_analyzer.llm.classifiers import BatchState, adapt_batch_size

    state = BatchState(
        current_size=initial_size,
        consecutive_failures=5,
        consecutive_successes=15,
    )
    new = adapt_batch_size(state, success=success, max_size=10)
    assert new.current_size >= 1


# ── LLM-01: enrich_prs_async ──────────────────────────────────────────────────


class _FakeAsyncClient:
    """Cliente async fake para testes — retorna classificação válida."""

    async def run(self, message: str, **kwargs: Any) -> Any:
        return MagicMock(
            content='{"tipo_projeto": "biblioteca", "natureza": "bug fix", "clareza": "boa"}'
        )


class _CountingAsyncClient:
    """Cliente async que conta chamadas simultâneas para validar Semaphore."""

    def __init__(self) -> None:
        self.concurrent = 0
        self.max_concurrent = 0

    async def run(self, message: str, **kwargs: Any) -> Any:
        self.concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent)
        await asyncio.sleep(0)  # cede controle ao event loop
        self.concurrent -= 1
        return MagicMock(
            content='{"tipo_projeto": "outro", "natureza": "outro", "clareza": "insuficiente"}'
        )


def test_enrich_prs_async_retorna_lista_enriched_pr(
    sample_pr: PRRecord,
) -> None:
    from pr_analyzer.llm.classifiers import enrich_prs_async

    prs = [sample_pr, sample_pr._replace(pr_id=2)]
    result = asyncio.run(enrich_prs_async(prs, _FakeAsyncClient(), concurrency=2))

    assert len(result) == 2
    assert all(isinstance(ep, EnrichedPR) for ep in result)


def test_enrich_prs_async_respeita_concurrency_limit(
    sample_pr: PRRecord,
) -> None:
    from pr_analyzer.llm.classifiers import enrich_prs_async

    # sample_pr tem body com conteúdo → não será curtada pela heurística
    prs = [sample_pr._replace(pr_id=i) for i in range(10)]
    counter = _CountingAsyncClient()

    asyncio.run(enrich_prs_async(prs, counter, concurrency=3))

    assert counter.max_concurrent <= 3


def test_enrich_prs_async_aplica_heuristica_sem_chamar_llm(
    sample_pr: PRRecord,
) -> None:
    from pr_analyzer.llm.classifiers import enrich_prs_async

    calls = 0

    class _SpyClient:
        async def run(self, message: str, **kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            return MagicMock(
                content='{"tipo_projeto": "outro", "natureza": "outro", "clareza": "insuficiente"}'
            )

    # PR com body vazio e natureza óbvia → heurística cobre sem chamar LLM
    pr_heuristic = sample_pr._replace(title="hotfix critical crash", body="")
    asyncio.run(enrich_prs_async([pr_heuristic], _SpyClient(), concurrency=4))

    assert calls == 0


def test_enrich_prs_async_campos_validos(sample_pr: PRRecord) -> None:
    from pr_analyzer.llm.classifiers import enrich_prs_async

    result = asyncio.run(
        enrich_prs_async([sample_pr], _FakeAsyncClient(), concurrency=1)
    )

    ep = result[0]
    assert ep.project_type in TIPOS_PROJETO
    assert ep.contribution_nature in NATUREZAS_CONTRIBUICAO
    assert ep.description_clarity in NIVEIS_CLAREZA_DESCRICAO


def test_enrich_prs_async_batch_agrupa_prs(sample_pr: PRRecord) -> None:
    from pr_analyzer.llm.classifiers import enrich_prs_async

    call_count = 0

    class _BatchSpyClient:
        async def run(self, message: str, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            # batch tool retorna array de classificações
            classifications = [
                {"tipo_projeto": "biblioteca", "natureza": "bug fix", "clareza": "boa"}
            ] * message.count("PR ")
            return MagicMock(content=json.dumps({"classifications": classifications}))

    # 4 PRs com body não vazio (heurística não cobre), batch_size=2 → 2 chamadas
    prs = [sample_pr._replace(pr_id=i) for i in range(4)]
    asyncio.run(enrich_prs_async(prs, _BatchSpyClient(), batch_size=2, concurrency=4))

    assert call_count == 2


def test_enrich_prs_async_lista_vazia_retorna_vazio() -> None:
    from pr_analyzer.llm.classifiers import enrich_prs_async

    result = asyncio.run(enrich_prs_async([], _FakeAsyncClient(), concurrency=4))
    assert result == []


def test_enrich_prs_async_fallback_em_erro_llm(sample_pr: PRRecord) -> None:
    from pr_analyzer.llm.classifiers import enrich_prs_async

    class _ErrorClient:
        async def run(self, message: str, **kwargs: Any) -> Any:
            raise RuntimeError("LLM offline")

    result = asyncio.run(enrich_prs_async([sample_pr], _ErrorClient(), concurrency=1))

    assert len(result) == 1
    assert result[0].project_type == "outro"


# ── LLM-09: _body_snippet ─────────────────────────────────────────────────────


def test_body_snippet_body_vazio_retorna_empty_marker() -> None:
    from pr_analyzer.llm.classifiers import _body_snippet

    assert _body_snippet("", 400) == "(empty)"


def test_body_snippet_so_espacos_retorna_empty_marker() -> None:
    from pr_analyzer.llm.classifiers import _body_snippet

    assert _body_snippet("   \n\t  ", 400) == "(empty)"


def test_body_snippet_trunca_no_limite() -> None:
    from pr_analyzer.llm.classifiers import _body_snippet

    assert _body_snippet("abcdefgh", 5) == "abcde"


def test_body_snippet_corpo_curto_retorna_inteiro() -> None:
    from pr_analyzer.llm.classifiers import _body_snippet

    assert _body_snippet("hello", 400) == "hello"


def test_body_snippet_strip_espacos_iniciais() -> None:
    from pr_analyzer.llm.classifiers import _body_snippet

    assert _body_snippet("  hello world  ", 5) == "hello"


# ── LLM-05: cache de tipo por repositório ────────────────────────────────────


def test_enrich_pr_with_tools_usa_tool_reduzida_com_cache(
    sample_pr: PRRecord,
) -> None:
    mock_client = MagicMock()
    mock_client.run.return_value = MagicMock(
        content='{"natureza": "bug fix", "clareza": "boa"}'
    )
    cache = {sample_pr.repo_name: "framework"}

    result = enrich_pr_with_tools(sample_pr, mock_client, repo_type_cache=cache)

    assert result.project_type == "framework"
    tools_used = mock_client.run.call_args[1]["tools"]
    assert tools_used[0]["function"]["name"] == "classify_pr_nature_clarity"


def test_enrich_pr_with_tools_sem_cache_usa_tool_completa(
    sample_pr: PRRecord,
) -> None:
    mock_client = MagicMock()
    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")

    enrich_pr_with_tools(sample_pr, mock_client, repo_type_cache=None)

    tools_used = mock_client.run.call_args[1]["tools"]
    assert tools_used[0]["function"]["name"] == "classify_pr"


def test_enrich_pr_with_tools_cache_preserva_tipo_mesmo_em_erro(
    sample_pr: PRRecord,
) -> None:
    mock_client = MagicMock()
    mock_client.run.side_effect = RuntimeError("timeout")
    cache = {sample_pr.repo_name: "ferramenta"}

    result = enrich_pr_with_tools(sample_pr, mock_client, repo_type_cache=cache)

    assert result.project_type == "ferramenta"


def test_enrich_pr_with_tools_nature_clarity_validos_com_cache(
    sample_pr: PRRecord,
) -> None:
    mock_client = MagicMock()
    mock_client.run.return_value = MagicMock(
        content='{"natureza": "feature", "clareza": "excelente"}'
    )
    cache = {sample_pr.repo_name: "biblioteca"}

    result = enrich_pr_with_tools(sample_pr, mock_client, repo_type_cache=cache)

    assert result.contribution_nature == "feature"
    assert result.description_clarity == "excelente"


def test_enrich_prs_pre_classifica_repos_com_use_tools(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """use_tools=True, batch_size=1: chama classify_repos_batch antes dos PRs."""
    # sample_pr tem body com conteúdo → heurística não cobre
    pr1 = sample_pr._replace(pr_id=1)
    pr2 = sample_pr._replace(pr_id=2)

    # 1a chamada: repo type (texto), demais: nature+clarity (tool reduzida)
    mock_client.run.side_effect = [
        MagicMock(content='{"tipo_projeto": "biblioteca"}'),  # repo type
        MagicMock(content='{"natureza": "bug fix", "clareza": "boa"}'),  # pr1
        MagicMock(content='{"natureza": "feature", "clareza": "boa"}'),  # pr2
    ]

    results = list(enrich_prs([pr1, pr2], mock_client, use_tools=True, batch_size=1))

    assert len(results) == 2
    # Tipo vem do cache (resultado da 1a chamada de repo), não de cada PR
    assert results[0].project_type == "biblioteca"
    assert results[1].project_type == "biblioteca"
    # Apenas 3 chamadas totais: 1 repo + 2 PRs (não 6)
    assert mock_client.run.call_count == 3


# ── LLM-06: enrich_prs com ClassificationMetrics ─────────────────────────────


def test_enrich_prs_com_metrics_conta_total_prs(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")
    m = ClassificationMetrics()
    list(enrich_prs([sample_pr, sample_pr], mock_client, use_tools=True, metrics=m))
    assert m.total_prs == 2


def test_enrich_prs_com_metrics_registra_value_counts(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")
    m = ClassificationMetrics()
    list(enrich_prs([sample_pr], mock_client, use_tools=True, metrics=m))
    assert m.value_counts.get("tipo_projeto", {}).get("biblioteca", 0) == 1
    assert m.value_counts.get("natureza", {}).get("bug fix", 0) == 1


def test_enrich_prs_com_metrics_registra_total_time(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    mock_client.run.return_value = _tool_response("biblioteca", "bug fix", "boa")
    m = ClassificationMetrics()
    list(enrich_prs([sample_pr], mock_client, use_tools=True, metrics=m))
    assert m.total_time_s >= 0.0


def test_enrich_prs_com_metrics_conta_batch_calls_serial(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """batch_size>1, max_workers=1: conta 1 batch_call por batch enviado."""
    from pr_analyzer.llm.metrics import ClassificationMetrics

    mock_client.run.return_value = _batch_response(
        [("biblioteca", "bug fix", "boa"), ("biblioteca", "bug fix", "boa")]
    )
    m = ClassificationMetrics()
    # 2 PRs com batch_size=5 → 1 batch
    list(
        enrich_prs(
            [sample_pr, sample_pr], mock_client, use_tools=True, batch_size=5, metrics=m
        )
    )
    assert m.batch_calls == 1


def test_enrich_prs_com_metrics_conta_batch_fallbacks_paralelo(
    mock_client: MagicMock, sample_pr: PRRecord
) -> None:
    """Batch que falha no paralelo incrementa batch_fallbacks."""
    from pr_analyzer.llm.metrics import ClassificationMetrics

    mock_client.run.side_effect = [
        MagicMock(content="not json"),  # batch falha
        _tool_response("biblioteca", "bug fix", "boa"),  # fallback individual
    ]
    m = ClassificationMetrics()
    # max_workers=2 usa _enrich_prs_batch_call (rastreia fallback)
    list(
        enrich_prs(
            [sample_pr],
            mock_client,
            use_tools=True,
            batch_size=5,
            max_workers=2,
            metrics=m,
        )
    )
    assert m.batch_fallbacks == 1
