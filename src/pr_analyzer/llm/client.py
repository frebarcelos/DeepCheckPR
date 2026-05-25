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
    return Agent(model=Groq(id=model_id, api_key=api_key))  # type: ignore[no-any-return]


class _OllamaDirectClient:
    """Cliente HTTP direto para Ollama usando apenas stdlib (urllib).

    Não depende do SDK ollama nem do agno.models.ollama (que exige openai).
    """

    def __init__(self, model: str, host: str) -> None:
        self._model = model
        self._host = host.rstrip("/")

    def run(self, message: str, **_: Any) -> Any:
        import json
        import urllib.request

        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": message}],
                "stream": False,
            }
        ).encode()
        req = urllib.request.Request(
            f"{self._host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())

        text = data.get("message", {}).get("content", "")

        class _Resp:
            def __init__(self, t: str) -> None:
                self.content = t

        return _Resp(text)


def create_ollama_client(model: str = "llama3") -> LLMClient:
    """Cria cliente direto para Ollama via SDK ollama (sem agno.models.ollama).

    Dentro do Docker no Linux, defina OLLAMA_HOST=http://host.docker.internal:11434.
    Localmente, o padrão http://localhost:11434 já funciona.
    """
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    return _OllamaDirectClient(model=model, host=host)


def create_llm_client() -> LLMClient:
    """Retorna cliente Groq ou Ollama com base em LLM_BACKEND no ambiente.

    LLM_BACKEND=groq  (padrão) → Groq API, requer GROQ_API_KEY
    LLM_BACKEND=ollama          → Ollama local, requer Ollama rodando
    LLM_MODEL sobrescreve o modelo padrão de cada backend.
    """
    backend = os.environ.get("LLM_BACKEND", "groq").lower()
    model = os.environ.get("LLM_MODEL", "")
    if backend == "ollama":
        return create_ollama_client(model or "llama3")
    return create_groq_client()
