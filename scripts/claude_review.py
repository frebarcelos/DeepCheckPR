#!/usr/bin/env python3
"""Revisão semântica de código via Claude API.

Executado no pre-push para arquivos Python modificados.
Verifica conformidade com paradigma funcional, TDD e Clean Code.

Requer: ANTHROPIC_API_KEY no ambiente ou no .env
Saída:  PASS / WARN / FAIL com comentários por arquivo
"""

import os
import subprocess
import sys
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """\
Você é um revisor especialista em Python 3.11 com foco em programação funcional.

Este projeto usa o paradigma funcional estrito. Avalie os arquivos enviados e retorne \
um relatório sucinto em português com:

## Regras críticas (retornar FAIL se violadas):
- FP001: Loop `for` em módulo puro (transforms/ ou pipeline/)
- FP002: Loop `while` em módulo puro
- FP003: Mutação por índice `x[i] = y` em módulo puro
- FP004: Métodos mutantes (.append, .update, .pop, .extend) em módulo puro
- FP005: I/O (open, print, write) em módulo puro
- FP006: Estado global mutável em módulo puro
- Ausência de testes para código de produção (TDD obrigatório)

## Boas práticas (retornar WARN se ausentes):
- BP001: Função pública sem anotação de retorno
- BP002: Função com mais de 30 linhas
- BP003: Função com mais de 5 parâmetros
- BP004: Parâmetro sem anotação de tipo
- FP007: Módulo puro sem uso de map/filter/reduce

## Formato da resposta:
STATUS: PASS | WARN | FAIL
ARQUIVOS ANALISADOS: <lista>

[Para cada problema encontrado:]
- ARQUIVO: <nome>
  REGRA: <código>
  LINHA: <número aproximado>
  PROBLEMA: <descrição>
  SUGESTÃO: <como corrigir>

RESUMO: <1-2 frases sobre a qualidade geral do código>

Seja conciso. Omita seções sem problemas.
"""


def _get_staged_python_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1..HEAD", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    files = [f for f in result.stdout.splitlines() if f.endswith(".py")]
    return files


def _read_file_safe(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def _build_user_message(files: list[str]) -> str:
    parts: list[str] = []
    for filepath in files:
        content = _read_file_safe(filepath)
        if content is None:
            continue
        parts.append(f"### {filepath}\n```python\n{content}\n```")
    return "\n\n".join(parts) if parts else ""


def _load_env() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    _load_env()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY não configurada — revisão Claude ignorada.")
        print("   Configure no .env ou exporte a variável para ativar a revisão semântica.")
        return 0

    files = _get_staged_python_files()
    if not files:
        print("claude-review: nenhum arquivo Python modificado.")
        return 0

    src_files = [f for f in files if "src/" in f]
    if not src_files:
        print("claude-review: nenhum arquivo de src/ para revisar.")
        return 0

    user_message = _build_user_message(src_files)
    if not user_message:
        return 0

    print(f"claude-review: revisando {len(src_files)} arquivo(s)...")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = next(
        (block.text for block in message.content if hasattr(block, "text")),
        "",
    )

    print("\n" + "─" * 60)
    print(response_text)
    print("─" * 60 + "\n")

    if response_text.startswith("STATUS: FAIL"):
        print("❌ claude-review: violações críticas encontradas — push bloqueado.")
        return 1

    if response_text.startswith("STATUS: WARN"):
        print("⚠️  claude-review: avisos encontrados — revise quando possível.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
