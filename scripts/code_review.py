#!/usr/bin/env python3
"""Executa a revisão determinística baseada nas regras locais do projeto.

O hook roda antes do push, aplica ``check_paradigm.py`` aos arquivos Python
do último commit e reporta PASS, WARN ou FAIL. Nenhum serviço de IA ou API
externa é necessário.
"""

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

SCRIPTS_DIR = Path(__file__).parent


def _get_committed_python_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1..HEAD", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [file for file in result.stdout.splitlines() if file.endswith(".py")]


def main() -> int:
    files = _get_committed_python_files()
    if not files:
        print("code-review: nenhum arquivo Python modificado.")
        return 0

    checker = SCRIPTS_DIR / "check_paradigm.py"
    result = subprocess.run(
        [sys.executable, str(checker), *files],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    output = result.stdout.strip()
    has_errors = result.returncode != 0
    has_warnings = "WARNING" in output

    print("\n" + "-" * 60)
    print("REVISAO DE CODIGO (regras locais)")
    print("-" * 60)

    print(output or "Nenhuma violacao encontrada.")
    print("-" * 60)

    if has_errors:
        print("STATUS: FAIL — violacoes criticas bloqueiam o push.")
        print(f"Arquivos revisados: {', '.join(files)}")
        return 1

    status = "WARN — avisos encontrados, revise quando possivel."
    if not has_warnings:
        status = "PASS — todos os arquivos conformes com o paradigma."
    print(f"STATUS: {status}")
    print(f"Arquivos revisados: {', '.join(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
