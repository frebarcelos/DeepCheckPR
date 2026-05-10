"""Testes para src/pr_analyzer/llm/classifiers.py — TASK-09."""

import os
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv

from pr_analyzer.llm.classifiers import (
    NATUREZAS_CONTRIBUICAO,
    NIVEIS_CLAREZA_DESCRICAO,
    TIPOS_PROJETO,
    avaliar_clareza_descricao,
    classificar_natureza_contribuicao,
    classificar_tipo_projeto,
)
from pr_analyzer.llm.client import create_groq_client


@pytest.fixture
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
    mock_client.run.return_value.content = 'invalid json'
    result = classificar_tipo_projeto("repo", ["title"], mock_client)
    assert result == "outro"


def test_classificar_tipo_projeto_fallback_invalid_value(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = '{"tipo_projeto": "valor_invalido"}'
    result = classificar_tipo_projeto("repo", ["title"], mock_client)
    assert result == "outro"


@pytest.mark.integration
def test_classificar_tipo_projeto_integration() -> None:
    load_dotenv()
    if "GROQ_API_KEY" not in os.environ:
        pytest.skip("Requer GROQ_API_KEY no .env")
    client = create_groq_client()
    result = classificar_tipo_projeto("django/django", ["fix admin bug", "add feature"], client)
    assert result in TIPOS_PROJETO


# ── classificar_natureza_contribuicao ──────────────────────────────────────────────


def test_classificar_natureza_contribuicao_parse_json(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = '{"natureza": "bug fix"}'
    result = classificar_natureza_contribuicao("Fix memory leak", "Body content", mock_client)
    assert result == "bug fix"
    prompt = mock_client.run.call_args[0][0]
    assert "JSON" in prompt.upper()


def test_classificar_natureza_contribuicao_truncates_body_to_300(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = '{"natureza": "outro"}'
    long_body = "A" * 500
    classificar_natureza_contribuicao("title", long_body, mock_client)
    prompt = mock_client.run.call_args[0][0]
    assert len(long_body) > 300
    assert "A" * 300 in prompt
    assert "A" * 301 not in prompt


def test_classificar_natureza_contribuicao_fallback_invalid_json(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = 'invalid'
    result = classificar_natureza_contribuicao("title", "body", mock_client)
    assert result == "outro"


def test_classificar_natureza_contribuicao_fallback_invalid_value(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = '{"natureza": "invalido"}'
    result = classificar_natureza_contribuicao("title", "body", mock_client)
    assert result == "outro"


# ── avaliar_clareza_descricao ──────────────────────────────────────────────


def test_avaliar_clareza_descricao_short_circuit_empty(mock_client: MagicMock) -> None:
    result = avaliar_clareza_descricao("   \n", mock_client)
    assert result == "insuficiente"
    mock_client.run.assert_not_called()


def test_avaliar_clareza_descricao_truncates_body_to_500(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = "boa"
    long_body = "B" * 600
    avaliar_clareza_descricao(long_body, mock_client)
    prompt = mock_client.run.call_args[0][0]
    assert "B" * 500 in prompt
    assert "B" * 501 not in prompt


def test_avaliar_clareza_descricao_valid_return(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = "excelente"
    result = avaliar_clareza_descricao("Good body", mock_client)
    assert result == "excelente"


def test_avaliar_clareza_descricao_fallback_invalid(mock_client: MagicMock) -> None:
    mock_client.run.return_value.content = "muito bom (invalido)"
    result = avaliar_clareza_descricao("Good body", mock_client)
    assert result == "insuficiente"
