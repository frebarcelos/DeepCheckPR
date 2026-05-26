"""Testes para src/pr_analyzer/llm/client.py — TASK-08."""

import http.client as _http
import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)  # type: ignore[misc]
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


# ── _OllamaDirectClient — helpers ─────────────────────────────────────────────


def _make_conn(content: str) -> MagicMock:
    """Mock de http.client.HTTPConnection que retorna `content` como resposta do modelo."""
    payload = json.dumps({"message": {"content": content}}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp
    return mock_conn


def _make_conn_tool(arguments: dict[str, Any]) -> MagicMock:
    """Mock que retorna uma resposta com tool_calls."""
    payload = json.dumps(
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "classify_pr", "arguments": arguments}}
                ],
            }
        }
    ).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp
    return mock_conn


def _captured_messages(mock_conn: MagicMock) -> list[dict[str, str]]:
    """Extrai a lista de mensagens do body enviado via conn.request()."""
    body_bytes: bytes = mock_conn.request.call_args.kwargs["body"]
    return json.loads(body_bytes.decode())["messages"]  # type: ignore[no-any-return]


def _get_request_body(mock_conn: MagicMock) -> dict[str, Any]:
    """Extrai o body JSON completo enviado via conn.request()."""
    body_bytes: bytes = mock_conn.request.call_args.kwargs["body"]
    return json.loads(body_bytes.decode())  # type: ignore[no-any-return]


# ── _OllamaDirectClient — testes ──────────────────────────────────────────────


def test_ollama_client_last_message_is_user_input() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(model="tinyllama", host="http://localhost:11434")
    mock_conn = _make_conn('{"ok": true}')
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("Hello model")

    msgs = _captured_messages(mock_conn)
    assert msgs[-1] == {"role": "user", "content": "Hello model"}


def test_ollama_client_includes_system_message_when_set() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(
        model="tinyllama",
        host="http://localhost:11434",
        system_prompt="Be JSON-only.",
    )
    mock_conn = _make_conn("{}")
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("test")

    msgs = _captured_messages(mock_conn)
    assert msgs[0] == {"role": "system", "content": "Be JSON-only."}


def test_ollama_client_no_system_message_when_empty_prompt() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(
        model="tinyllama", host="http://localhost:11434", system_prompt=""
    )
    mock_conn = _make_conn("{}")
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("test")

    msgs = _captured_messages(mock_conn)
    assert all(m["role"] != "system" for m in msgs)


def test_ollama_client_interleaves_shots_before_real_query() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(
        model="tinyllama", host="http://localhost:11434", system_prompt=""
    )
    shots = (("example input 1", '{"a": "1"}'), ("example input 2", '{"a": "2"}'))
    mock_conn = _make_conn('{"a": "3"}')
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("real question", shots=shots)

    msgs = _captured_messages(mock_conn)
    user_shots = [
        m for m in msgs if m["role"] == "user" and m["content"] != "real question"
    ]
    assistant_shots = [m for m in msgs if m["role"] == "assistant"]
    assert len(user_shots) == 2
    assert len(assistant_shots) == 2
    assert msgs[-1] == {"role": "user", "content": "real question"}


def test_ollama_client_without_shots_sends_single_user_message() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(
        model="tinyllama", host="http://localhost:11434", system_prompt=""
    )
    mock_conn = _make_conn("{}")
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("only message")

    msgs = _captured_messages(mock_conn)
    assert len(msgs) == 1
    assert msgs[0] == {"role": "user", "content": "only message"}


def test_ollama_client_returns_content_from_response() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(model="tinyllama", host="http://localhost:11434")
    mock_conn = _make_conn('{"tipo_projeto": "biblioteca"}')
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        result = client.run("classify this")

    assert result.content == '{"tipo_projeto": "biblioteca"}'


def test_create_ollama_client_uses_classifier_system_prompt() -> None:
    from pr_analyzer.llm.client import create_ollama_client
    from pr_analyzer.llm.skills import CLASSIFIER_SYSTEM_PROMPT

    with patch.dict(os.environ, {"OLLAMA_HOST": "http://localhost:11434"}):
        client = create_ollama_client(model="tinyllama")

    mock_conn = _make_conn("{}")
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("test")

    msgs = _captured_messages(mock_conn)
    system_msgs = [m for m in msgs if m["role"] == "system"]
    assert len(system_msgs) == 1
    assert system_msgs[0]["content"] == CLASSIFIER_SYSTEM_PROMPT


# ── tool calling ──────────────────────────────────────────────────────────────


def test_ollama_client_inclui_tools_no_payload() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(model="qwen2:1.5b", host="http://localhost:11434")
    tools = [
        {"type": "function", "function": {"name": "classify_pr", "parameters": {}}}
    ]
    mock_conn = _make_conn("{}")
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("classify this PR", tools=tools)

    body = _get_request_body(mock_conn)
    assert "tools" in body
    assert body["tools"] == tools


def test_ollama_client_sem_tools_nao_inclui_campo_tools() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(model="tinyllama", host="http://localhost:11434")
    mock_conn = _make_conn("{}")
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        client.run("classify this PR")

    body = _get_request_body(mock_conn)
    assert "tools" not in body


def test_ollama_client_tool_call_response_vira_json_no_content() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    args = {"tipo_projeto": "framework", "natureza": "bug fix", "clareza": "boa"}
    client = _OllamaDirectClient(model="qwen2:1.5b", host="http://localhost:11434")
    mock_conn = _make_conn_tool(args)
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        result = client.run("classify PR", tools=[{}])

    parsed = json.loads(result.content)
    assert parsed == args


def test_ollama_client_sem_tool_call_usa_content_normal() -> None:
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(model="tinyllama", host="http://localhost:11434")
    mock_conn = _make_conn('{"clareza": "boa"}')
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        result = client.run("classify PR")

    assert result.content == '{"clareza": "boa"}'


# ── LLM-03: HTTP keep-alive ───────────────────────────────────────────────────


def test_ollama_client_reusa_conexao_entre_chamadas() -> None:
    """Múltiplas chamadas run() reusam a mesma conexão TCP (keep-alive)."""
    from pr_analyzer.llm.client import _OllamaDirectClient

    client = _OllamaDirectClient(model="tinyllama", host="http://localhost:11434")
    mock_conn = _make_conn('{"ok": true}')
    with patch("http.client.HTTPConnection", return_value=mock_conn) as mock_cls:
        client.run("first call")
        client.run("second call")

    assert mock_cls.call_count == 1  # construtor chamado 1x — conexão reutilizada


def test_ollama_client_reconecta_se_conexao_fechada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quando o servidor fecha a conexão, reconecta e retenta automaticamente."""
    from pr_analyzer.llm.client import _OllamaDirectClient

    monkeypatch.setenv("LLM_MAX_RETRIES", "2")
    monkeypatch.setenv("LLM_RETRY_BASE_DELAY", "0.0")

    client = _OllamaDirectClient(model="tinyllama", host="http://localhost:11434")
    conn_broken = MagicMock()
    conn_broken.getresponse.side_effect = _http.RemoteDisconnected("server closed")
    conn_fresh = _make_conn('{"ok": true}')

    with patch(
        "http.client.HTTPConnection", side_effect=[conn_broken, conn_fresh]
    ) as mock_cls:
        result = client.run("hello")

    assert mock_cls.call_count == 2  # nova conexão criada após desconexão
    assert result.content == '{"ok": true}'


# ── _with_retry ───────────────────────────────────────────────────────────────


def test_with_retry_sucesso_na_primeira_tentativa() -> None:
    from pr_analyzer.llm.client import _with_retry

    calls: list[int] = []

    def fn() -> str:
        calls.append(1)
        return "ok"

    result = _with_retry(fn, max_attempts=3, base_delay=0.0)
    assert result == "ok"
    assert len(calls) == 1


def test_with_retry_sucesso_na_terceira_tentativa() -> None:
    from pr_analyzer.llm.client import _with_retry

    calls: list[int] = []

    def fn() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("ainda não")
        return "ok"

    result = _with_retry(fn, max_attempts=3, base_delay=0.0)
    assert result == "ok"
    assert len(calls) == 3


def test_with_retry_levanta_excecao_apos_max_attempts() -> None:
    from pr_analyzer.llm.client import _with_retry

    def fn() -> str:
        raise RuntimeError("sempre falha")

    with pytest.raises(RuntimeError, match="sempre falha"):
        _with_retry(fn, max_attempts=3, base_delay=0.0)


def test_with_retry_respeita_backoff_exponencial() -> None:
    from pr_analyzer.llm.client import _with_retry

    slept: list[float] = []

    def fn() -> str:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        _with_retry(fn, max_attempts=3, base_delay=2.0, _sleep=slept.append)

    # 3 tentativas → 2 sleeps entre elas: 2.0^0*2=2.0, 2.0^1*2=4.0
    assert slept == [2.0, 4.0]


def test_with_retry_sem_sleep_na_ultima_tentativa() -> None:
    from pr_analyzer.llm.client import _with_retry

    slept: list[float] = []

    def fn() -> str:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        _with_retry(fn, max_attempts=1, base_delay=5.0, _sleep=slept.append)

    assert slept == []


def test_with_retry_propaga_ultima_excecao() -> None:
    from pr_analyzer.llm.client import _with_retry

    class _CustomError(Exception):
        pass

    attempts = [0]

    def fn() -> str:
        attempts[0] += 1
        raise _CustomError(f"erro na tentativa {attempts[0]}")

    with pytest.raises(_CustomError, match="erro na tentativa 3"):
        _with_retry(fn, max_attempts=3, base_delay=0.0)


# ── LLM-01: AsyncLLMClient e _AsyncOllamaClient ──────────────────────────────


def test_async_ollama_client_delega_para_sync_client() -> None:
    import asyncio

    from pr_analyzer.llm.client import _AsyncOllamaClient

    mock_sync = MagicMock()
    mock_sync.run.return_value = MagicMock(content='{"ok": true}')
    client = _AsyncOllamaClient(mock_sync)

    result = asyncio.run(client.run("hello"))

    mock_sync.run.assert_called_once_with("hello")
    assert result.content == '{"ok": true}'


def test_async_ollama_client_propaga_kwargs() -> None:
    import asyncio

    from pr_analyzer.llm.client import _AsyncOllamaClient

    mock_sync = MagicMock()
    mock_sync.run.return_value = MagicMock(content="{}")
    client = _AsyncOllamaClient(mock_sync)
    tools = [{"type": "function"}]

    asyncio.run(client.run("msg", tools=tools))

    _args, kwargs = mock_sync.run.call_args
    assert kwargs.get("tools") == tools


def test_async_ollama_client_satisfaz_protocol() -> None:
    import asyncio

    from pr_analyzer.llm.client import AsyncLLMClient, _AsyncOllamaClient

    mock_sync = MagicMock()
    mock_sync.run.return_value = MagicMock(content="{}")
    client: AsyncLLMClient = _AsyncOllamaClient(mock_sync)

    result = asyncio.run(client.run("test"))
    assert result.content == "{}"


def test_create_async_ollama_client_retorna_async_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pr_analyzer.llm.client import _AsyncOllamaClient, create_async_ollama_client

    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    client = create_async_ollama_client(model="tinyllama")

    assert isinstance(client, _AsyncOllamaClient)


def test_create_async_llm_client_ollama_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pr_analyzer.llm.client import _AsyncOllamaClient, create_async_llm_client

    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    client = create_async_llm_client()

    assert isinstance(client, _AsyncOllamaClient)
