"""Testes para src/pr_analyzer/llm/client.py — TASK-08."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _patch_agno() -> object:
    """Impede que o módulo agno seja chamado de verdade em qualquer teste."""
    with (
        patch("pr_analyzer.llm.client.Agent", return_value=MagicMock()),
        patch("pr_analyzer.llm.client.Groq", return_value=MagicMock()),
    ):
        yield


def test_create_groq_client_lê_api_key_do_ambiente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_MODEL", "llama3-8b-8192")

    with patch("pr_analyzer.llm.client.Groq") as mock_groq:
        from pr_analyzer.llm.client import create_groq_client

        create_groq_client()

        mock_groq.assert_called_once_with(id="llama3-8b-8192", api_key="test-key-123")


def test_create_groq_client_usa_modelo_padrao_sem_llm_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with patch("pr_analyzer.llm.client.Groq") as mock_groq:
        from pr_analyzer.llm.client import create_groq_client

        create_groq_client()

        _args, kwargs = mock_groq.call_args
        assert kwargs.get("id") == "llama3-8b-8192"


def test_create_groq_client_levanta_sem_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from pr_analyzer.llm.client import create_groq_client

    with pytest.raises(KeyError):
        create_groq_client()


def test_create_groq_client_passa_api_key_para_groq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "minha-chave-secreta")
    monkeypatch.setenv("LLM_MODEL", "llama3-70b-8192")

    with patch("pr_analyzer.llm.client.Groq") as mock_groq:
        from pr_analyzer.llm.client import create_groq_client

        create_groq_client()

        mock_groq.assert_called_once_with(
            id="llama3-70b-8192", api_key="minha-chave-secreta"
        )
