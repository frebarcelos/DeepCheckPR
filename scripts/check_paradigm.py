#!/usr/bin/env python3
"""Verificador de conformidade com o paradigma funcional via análise de AST.

Executado pelo pre-commit em cada git commit nos arquivos modificados.
Analisa o código sem executá-lo — zero dependências externas além da stdlib.

Dois níveis de verificação:
  ERROR   → bloqueia o commit (violação grave do paradigma ou boas práticas)
  WARNING → exibe aviso mas permite o commit (melhoria recomendada)
"""

import ast
import sys
from pathlib import Path
from typing import NamedTuple

# Módulos que devem ser puramente funcionais (sem efeitos colaterais)
PURE_MODULES = frozenset({"transforms", "pipeline"})

# Métodos que mutam estruturas in-place — proibidos em módulos puros
MUTATING_METHODS = frozenset({
    "append", "extend", "update", "pop", "remove",
    "insert", "clear", "sort", "reverse", "setdefault", "discard",
})

# Funções de I/O — proibidas em módulos puros
IO_FUNCTIONS = frozenset({"open", "print", "input", "write"})

# Máximo de linhas por função (Clean Code)
MAX_FUNCTION_LINES = 30

# Máximo de parâmetros por função (Clean Code)
MAX_PARAMETERS = 5


class Issue(NamedTuple):
    filepath: str
    line: int
    level: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.filepath}:{self.line}: [{self.rule}] {self.level}: {self.message}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_pure_module(filepath: str) -> bool:
    """Retorna True se o arquivo pertence a uma camada puramente funcional."""
    return any(part in PURE_MODULES for part in Path(filepath).parts)


def _is_src_file(filepath: str) -> bool:
    """Retorna True se o arquivo é código-fonte (não teste, não script)."""
    parts = Path(filepath).parts
    return "src" in parts and "test" not in filepath


# ---------------------------------------------------------------------------
# Verificador de módulos puros (transforms/ e pipeline/)
# ---------------------------------------------------------------------------

class PureModuleChecker(ast.NodeVisitor):
    """Verifica violações do paradigma funcional em módulos sem efeitos colaterais."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.issues: list[Issue] = []

    def _err(self, node: ast.AST, rule: str, msg: str) -> None:
        self.issues.append(Issue(self.filepath, getattr(node, "lineno", 0), "ERROR", rule, msg))

    def _warn(self, node: ast.AST, rule: str, msg: str) -> None:
        self.issues.append(Issue(self.filepath, getattr(node, "lineno", 0), "WARNING", rule, msg))

    def visit_For(self, node: ast.For) -> None:
        self._err(node, "FP001",
            "Loop 'for' em módulo puro. "
            "Use map(), filter(), reduce(), generator expression ou itertools."
        )
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._err(node, "FP002",
            "Loop 'while' em módulo puro. "
            "Use recursão ou funções de itertools para repetição funcional."
        )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            # x[i] = y  →  mutação in-place
            if isinstance(target, ast.Subscript):
                self._err(node, "FP003",
                    "Atribuição por índice 'x[i] = y' detectada. "
                    "Retorne uma nova estrutura: dict | {k: v} ou tuple(...)."
                )
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # x += y  em subscript → mutação
        if isinstance(node.target, ast.Subscript):
            self._err(node, "FP003",
                "Atribuição aumentada em índice 'x[i] += y'. "
                "Retorne uma nova estrutura em vez de modificar in-place."
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            # Métodos mutantes: .append(), .update(), etc.
            if node.func.attr in MUTATING_METHODS:
                self._err(node, "FP004",
                    f"Método mutante '.{node.func.attr}()' detectado. "
                    "Alternativas imutáveis: list + [x], dict | {{k: v}}, frozenset | {{x}}."
                )
            # I/O em módulo puro
            if node.func.attr in {"write", "read", "readline", "readlines"}:
                self._err(node, "FP005",
                    f"Operação de I/O '.{node.func.attr}()' em módulo puro. "
                    "Isole I/O no módulo io/."
                )

        if isinstance(node.func, ast.Name):
            if node.func.id == "open":
                self._err(node, "FP005",
                    "Chamada 'open()' em módulo puro. Isole I/O no módulo io/."
                )

        self.generic_visit(node)

    def _check_module_globals(self, tree: ast.Module) -> None:
        """Detecta estado global mutável no escopo do módulo."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
                            self._err(node, "FP006",
                                f"Estado global mutável '{target.id} = {type(node.value).__name__}' detectado. "
                                "Use frozenset, tuple ou NamedTuple para estruturas imutáveis no escopo do módulo."
                            )


# ---------------------------------------------------------------------------
# Verificador de boas práticas (todos os arquivos src/)
# ---------------------------------------------------------------------------

class BestPracticesChecker(ast.NodeVisitor):
    """Verifica princípios de Clean Code e boas práticas Python."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.issues: list[Issue] = []

    def _err(self, node: ast.AST, rule: str, msg: str) -> None:
        self.issues.append(Issue(self.filepath, getattr(node, "lineno", 0), "ERROR", rule, msg))

    def _warn(self, node: ast.AST, rule: str, msg: str) -> None:
        self.issues.append(Issue(self.filepath, getattr(node, "lineno", 0), "WARNING", rule, msg))

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        is_private = node.name.startswith("_")
        is_dunder = node.name.startswith("__") and node.name.endswith("__")

        # Anotação de retorno obrigatória em funções públicas
        if node.returns is None and not is_dunder:
            self._warn(node, "BP001",
                f"Função '{node.name}' sem anotação de retorno '-> tipo'. "
                "Anotações são obrigatórias para type checking com mypy --strict."
            )

        # Comprimento da função
        end = getattr(node, "end_lineno", node.lineno)
        length = end - node.lineno
        if length > MAX_FUNCTION_LINES:
            self._warn(node, "BP002",
                f"Função '{node.name}' tem {length} linhas (máximo: {MAX_FUNCTION_LINES}). "
                "Funções longas violam Clean Code — divida em funções menores e bem nomeadas."
            )

        # Número de parâmetros
        n_args = len(node.args.args) + len(node.args.posonlyargs)
        if n_args > MAX_PARAMETERS:
            self._warn(node, "BP003",
                f"Função '{node.name}' tem {n_args} parâmetros (máximo: {MAX_PARAMETERS}). "
                "Considere agrupar parâmetros em NamedTuple ou dict de configuração."
            )

        # Anotações nos parâmetros (funções públicas não privadas)
        if not is_private:
            for arg in node.args.args:
                if arg.annotation is None and arg.arg != "self":
                    self._warn(node, "BP004",
                        f"Parâmetro '{arg.arg}' em '{node.name}' sem anotação de tipo. "
                        "Use anotações em todas as funções públicas."
                    )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_module_globals(self, tree: ast.Module) -> None:
        """Detecta variáveis globais mutáveis no nível do módulo."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id.isupper()
                        and isinstance(node.value, (ast.List, ast.Dict, ast.Set))
                    ):
                        self._err(node, "BP005",
                            f"Constante global mutável '{target.id}'. "
                            "Use frozenset{{...}} ou tuple(...) para garantir imutabilidade."
                        )


# ---------------------------------------------------------------------------
# Verificador de paradigma funcional (heurística de uso real)
# ---------------------------------------------------------------------------

class FunctionalUsageChecker(ast.NodeVisitor):
    """Verifica se o código usa construções funcionais onde deveria."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.issues: list[Issue] = []
        self._functional_calls: set[str] = set()
        self._has_reduce_import = False

    def _warn(self, node: ast.AST, rule: str, msg: str) -> None:
        self.issues.append(Issue(self.filepath, getattr(node, "lineno", 0), "WARNING", rule, msg))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "functools":
            for alias in node.names:
                if alias.name in {"reduce", "lru_cache", "partial"}:
                    self._has_reduce_import = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self._functional_calls.add(node.func.id)
        self.generic_visit(node)

    def check_summary(self, tree: ast.Module) -> None:
        """Após visitar a árvore, verifica uso agregado de construções funcionais."""
        self.visit(tree)

        # Em módulos de transforms: espera-se uso de map/filter/reduce
        if _is_pure_module(self.filepath):
            functional_used = self._functional_calls & {"map", "filter", "reduce"}
            if not functional_used and not self.filepath.endswith("__init__.py"):
                self._warn(
                    ast.Module(body=[], type_ignores=[]),
                    "FP007",
                    "Nenhuma chamada a map(), filter() ou reduce() detectada neste módulo puro. "
                    "Verifique se o paradigma funcional está sendo aplicado corretamente."
                )


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def check_file(filepath: str) -> list[Issue]:
    issues: list[Issue] = []

    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as exc:
        issues.append(Issue(filepath, exc.lineno or 0, "ERROR", "SYN001", f"Erro de sintaxe: {exc.msg}"))
        return issues
    except OSError as exc:
        issues.append(Issue(filepath, 0, "ERROR", "SYN002", f"Não foi possível ler o arquivo: {exc}"))
        return issues

    # Boas práticas em todos os arquivos src/
    if _is_src_file(filepath):
        bp = BestPracticesChecker(filepath)
        bp._check_module_globals(tree)
        bp.visit(tree)
        issues.extend(bp.issues)

    # Paradigma funcional estrito apenas em módulos puros
    if _is_pure_module(filepath):
        pure = PureModuleChecker(filepath)
        pure._check_module_globals(tree)
        pure.visit(tree)
        issues.extend(pure.issues)

        usage = FunctionalUsageChecker(filepath)
        usage.check_summary(tree)
        issues.extend(usage.issues)

    return issues


def main() -> int:
    files = sys.argv[1:]
    if not files:
        return 0

    all_issues: list[Issue] = []
    for filepath in files:
        if filepath.endswith(".py"):
            all_issues.extend(check_file(filepath))

    errors = [i for i in all_issues if i.level == "ERROR"]
    warnings = [i for i in all_issues if i.level == "WARNING"]

    for issue in sorted(all_issues, key=lambda i: (i.filepath, i.line)):
        prefix = "❌" if issue.level == "ERROR" else "⚠️ "
        print(f"{prefix} {issue}")

    if all_issues:
        print()

    if errors:
        print(f"❌ {len(errors)} erro(s) — commit bloqueado. Corrija as violações acima.")
    if warnings:
        print(f"⚠️  {len(warnings)} aviso(s) de boas práticas — revise quando possível.")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
