#!/usr/bin/env python3
"""Executa hooks com o ambiente Python local do DeepCheckPR."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _python_candidates() -> tuple[Path, ...]:
    configured = os.environ.get("DEEPCHECKPR_PYTHON", "").strip()
    discovered = tuple(
        Path(executable)
        for command in ("python3", "python")
        if (executable := shutil.which(command)) is not None
    )
    explicit = (Path(configured),) if configured else ()
    return (
        *explicit,
        PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / ".venv" / "bin" / "python",
        *discovered,
    )


def _has_pytest(executable: Path) -> bool:
    if not executable.is_file():
        return False
    result = subprocess.run(
        [str(executable), "-c", "import pytest"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    (PROJECT_ROOT / ".cache").mkdir(parents=True, exist_ok=True)
    python = next(filter(_has_pytest, _python_candidates()), None)
    if python is None:
        print(
            "Ambiente de testes não encontrado. Crie .venv e execute "
            '`pip install -e ".[dev]"` antes do push.',
            file=sys.stderr,
        )
        return 1
    return subprocess.call([str(python), *sys.argv[1:]], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
