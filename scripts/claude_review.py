#!/usr/bin/env python3
"""Revisão de código baseada em regras locais pré-estabelecidas.

Executado no pre-push. Roda o verificador de paradigma (check_paradigm.py)
nos arquivos Python do último commit e reporta PASS / WARN / FAIL.

Zero chamadas de API — revisão determinística e sem custo.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def _get_committed_python_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1..HEAD", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.splitlines() if f.endswith(".py")]


def main() -> int:
    files = _get_committed_python_files()
    if not files:
        print("claude-review: nenhum arquivo Python modificado.")
        return 0

    checker = SCRIPTS_DIR / "check_paradigm.py"
    result = subprocess.run(
        [sys.executable, str(checker), *files],
        capture_output=True,
        text=True,
    )

    output = result.stdout.strip()
    has_errors = result.returncode != 0
    has_warnings = "WARNING" in output

    print("\n" + "-" * 60)
    print("REVISAO DE CODIGO (regras locais)")
    print("-" * 60)

    if output:
        print(output)
    else:
        print("Nenhuma violacao encontrada.")

    print("-" * 60)

    if has_errors:
        print("STATUS: FAIL — violacoes criticas bloqueiam o push.")
        print(f"Arquivos revisados: {', '.join(files)}")
        return 1

    if has_warnings:
        print("STATUS: WARN — avisos encontrados, revise quando possivel.")
    else:
        print("STATUS: PASS — todos os arquivos conformes com o paradigma.")

    print(f"Arquivos revisados: {', '.join(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
