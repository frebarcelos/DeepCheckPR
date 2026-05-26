"""Efeito colateral: configuração do cliente LLM via Agno/Groq."""

import asyncio
import http.client
import json
import os
import threading
import time
import urllib.parse
from collections.abc import Callable
from typing import Any, Protocol

from agno.agent import Agent
from agno.models.groq import Groq

from pr_analyzer.llm.skills import CLASSIFIER_SYSTEM_PROMPT

# ── Retry com backoff exponencial ────────────────────────────────────────────


def _with_retry(
    fn: Callable[[], Any],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    _sleep: Callable[[float], None] | None = None,
) -> Any:
    """Tenta fn até max_attempts vezes com backoff exponencial entre falhas.

    Args:
        fn: callable sem argumentos a executar.
        max_attempts: número máximo de tentativas (≥1).
        base_delay: delay base em segundos; tentativa k dorme base_delay * 2^k.
        _sleep: substituto de time.sleep para testes (injeta delays sem bloquear).

    Returns:
        Resultado de fn() na primeira tentativa bem-sucedida.

    Raises:
        Exception: última exceção levantada por fn após esgotar max_attempts.
    """
    sleep = _sleep if _sleep is not None else time.sleep
    last_exc: Exception = RuntimeError("_with_retry: nenhuma tentativa executada")
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                sleep(base_delay * (2.0**attempt))
    raise last_exc


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


# ── LLM-03: Thread-local storage para keep-alive ─────────────────────────────


class _ThreadLocalConn(threading.local):
    """Thread-local para armazenar conexões HTTP persistentes por thread."""

    def __init__(self) -> None:
        super().__init__()
        self.conn: http.client.HTTPConnection | None = None


class _OllamaDirectClient:
    """Cliente HTTP direto para Ollama usando apenas stdlib.

    LLM-03: reutiliza conexão TCP por thread (HTTP keep-alive) via
    http.client.HTTPConnection + threading.local. Reconecta automaticamente
    em caso de RemoteDisconnected ou outros erros de transporte.
    """

    def __init__(
        self,
        model: str,
        host: str,
        system_prompt: str = "",
    ) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._system_prompt = system_prompt
        parsed = urllib.parse.urlparse(self._host)
        self._netloc: str = parsed.netloc
        self._use_https: bool = parsed.scheme == "https"
        self._local: _ThreadLocalConn = _ThreadLocalConn()

    def _get_connection(self) -> http.client.HTTPConnection:
        """Retorna conexão thread-local, criando-a se necessário."""
        if self._local.conn is None:
            if self._use_https:
                self._local.conn = http.client.HTTPSConnection(
                    self._netloc, timeout=120
                )
            else:
                self._local.conn = http.client.HTTPConnection(self._netloc, timeout=120)
        conn = self._local.conn
        assert conn is not None
        return conn

    def run(self, message: str, **kwargs: Any) -> Any:
        shots: tuple[tuple[str, str], ...] = kwargs.get("shots", ())
        tools: list[dict[str, Any]] | None = kwargs.get("tools")

        messages: list[dict[str, str]] = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        for user_shot, assistant_shot in shots:
            messages.append({"role": "user", "content": user_shot})
            messages.append({"role": "assistant", "content": assistant_shot})
        messages.append({"role": "user", "content": message})

        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            body["tools"] = tools

        payload = json.dumps(body).encode()
        max_retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))
        retry_delay = float(os.environ.get("LLM_RETRY_BASE_DELAY", "1.0"))

        def _do_call() -> dict[str, Any]:
            conn = self._get_connection()
            try:
                conn.request(
                    "POST",
                    "/api/chat",
                    body=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp = conn.getresponse()
                return json.loads(resp.read().decode())  # type: ignore[no-any-return]
            except (http.client.HTTPException, OSError):
                self._local.conn = None  # força reconexão na próxima tentativa
                raise

        data: dict[str, Any] = _with_retry(
            _do_call, max_attempts=max_retries, base_delay=retry_delay
        )

        msg = data.get("message", {})
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            args: dict[str, Any] = (
                tool_calls[0].get("function", {}).get("arguments", {})
            )
            text = json.dumps(args)
        else:
            text = msg.get("content", "")

        class _Resp:
            def __init__(self, t: str) -> None:
                self.content = t

        return _Resp(text)


def create_ollama_client(
    model: str = "llama3",
    system_prompt: str = CLASSIFIER_SYSTEM_PROMPT,
) -> LLMClient:
    """Cria cliente direto para Ollama com system_prompt e suporte a shots.

    Dentro do Docker no Linux, defina OLLAMA_HOST=http://host.docker.internal:11434.
    Localmente, o padrão http://localhost:11434 já funciona.
    O system_prompt padrão (CLASSIFIER_SYSTEM_PROMPT) é otimizado para JSON-only,
    o que melhora drasticamente a confiabilidade em modelos pequenos como tinyllama.
    """
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    return _OllamaDirectClient(model=model, host=host, system_prompt=system_prompt)


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


# ── LLM-01: Cliente assíncrono ────────────────────────────────────────────────


class AsyncLLMClient(Protocol):
    """Interface assíncrona que qualquer cliente LLM async deve satisfazer.

    Espelha LLMClient, mas com async def run() para uso com asyncio.gather().
    """

    async def run(self, message: str, **kwargs: Any) -> Any:
        """Envia mensagem ao LLM de forma assíncrona."""
        ...


class _AsyncOllamaClient:
    """Wrapper assíncrono sobre LLMClient usando asyncio.to_thread.

    Não requer aiohttp — usa o thread pool padrão do asyncio para executar
    as chamadas de rede síncronas sem bloquear o event loop. Compatível com
    asyncio.gather() e asyncio.Semaphore para controle de concorrência.
    """

    def __init__(self, sync_client: LLMClient) -> None:
        self._sync = sync_client

    async def run(self, message: str, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._sync.run, message, **kwargs)


def create_async_ollama_client(
    model: str = "llama3",
    system_prompt: str = CLASSIFIER_SYSTEM_PROMPT,
) -> _AsyncOllamaClient:
    """Cria cliente Ollama assíncrono wrapeando o cliente síncrono."""
    sync = create_ollama_client(model=model, system_prompt=system_prompt)
    return _AsyncOllamaClient(sync)


def create_async_llm_client() -> _AsyncOllamaClient:
    """Retorna cliente async Ollama com base em LLM_BACKEND e LLM_MODEL no ambiente.

    Nota: o backend Groq não tem suporte nativo a asyncio nesta versão.
    Para Groq, o wrapper asyncio.to_thread ainda oferece concorrência via threads.
    """
    model = os.environ.get("LLM_MODEL", "llama3")
    return create_async_ollama_client(model=model)
