"""Testes para src/pr_analyzer/llm/classifiers.py — TASK-09, TASK-34, TASK-35."""

import os
from pathlib import Path
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
    enrich_prs,
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
    pr_sem_body = sample_pr._replace(body="")
    mock_client.run.side_effect = [
        MagicMock(content='{"tipo_projeto": "biblioteca"}'),
        MagicMock(content='{"natureza": "bug fix"}'),
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
