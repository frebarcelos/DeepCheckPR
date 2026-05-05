"""Efeito colateral: configuração do cliente LLM via Agno/Groq."""

import os
from typing import Any, Protocol

from agno.agent import Agent
from agno.models.groq import Groq


class LLMClient(Protocol):
    """Interface mínima que qualquer cliente LLM deve satisfazer.

    Usando Protocol em vez de Agent diretamente para facilitar mocks
    nos testes e desacoplar os classificadores da implementação concreta.
    """

    def run(self, message: str, **kwargs: Any) -> Any:
        """Envia uma mensagem ao LLM e retorna a resposta."""
        ...


def create_groq_client() -> LLMClient:
    """Cria e retorna agente Agno configurado com Groq.

    Lê GROQ_API_KEY e LLM_MODEL do ambiente. Carregue o .env antes
    de chamar esta função (ex: via python-dotenv na inicialização da UI).

    Raises:
        KeyError: se GROQ_API_KEY não estiver definido no ambiente.
    """
    api_key = os.environ["GROQ_API_KEY"]
    model_id = os.environ.get("LLM_MODEL", "llama3-8b-8192")
    return Agent(model=Groq(id=model_id, api_key=api_key))
