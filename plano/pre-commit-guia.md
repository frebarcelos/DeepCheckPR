# Guia de Pre-commit Hooks

## Quando cada hook roda

| Hook | Trigger | Velocidade | O que faz |
|---|---|---|---|
| `ruff` | `git commit` | Rápido | Linting + imports + complexidade + naming |
| `ruff-format` | `git commit` | Rápido | Formatação automática do código |
| `mypy` | `git commit` | Médio | Type checking estrito |
| `check-paradigm` | `git commit` | Rápido | Paradigma funcional + boas práticas (AST) |
| `debug-statements` | `git commit` | Rápido | Bloqueia `print()` e `breakpoint()` |
| `check-added-large-files` | `git commit` | Rápido | Impede commitar o CSV do dataset |
| `pytest-unit` | `git push` | Lento | Todos os testes unitários |
| `coverage-check` | `git push` | Lento | Cobertura mínima de 80% |

---

## Regras do verificador de paradigma (`check_paradigm.py`)

O verificador analisa o AST (árvore sintática) do código — não executa o código.
Erros bloqueiam o commit. Avisos são exibidos mas permitem o commit.

### Módulos puros: `transforms/` e `pipeline/`

Estas camadas devem ser **100% funcionais e sem efeitos colaterais**.

| Código | Nível | O que detecta |
|---|---|---|
| `FP001` | **ERROR** | Loop `for` — use `map()`, `filter()`, generator expression |
| `FP002` | **ERROR** | Loop `while` — use recursão ou `itertools` |
| `FP003` | **ERROR** | Atribuição por índice `x[i] = y` — retorne nova estrutura |
| `FP004` | **ERROR** | Método mutante: `.append()`, `.update()`, `.extend()`, `.pop()`, etc. |
| `FP005` | **ERROR** | I/O em módulo puro: `open()`, `.write()`, `.read()` — mova para `io/` |
| `FP006` | **ERROR** | Estado global mutável: `LISTA = []` — use `tuple` ou `frozenset` |
| `FP007` | **WARNING** | Módulo puro sem nenhum `map()`, `filter()` ou `reduce()` |

### Todos os arquivos `src/`

| Código | Nível | O que detecta |
|---|---|---|
| `BP001` | **WARNING** | Função sem anotação de retorno `-> tipo` |
| `BP002` | **WARNING** | Função com mais de 30 linhas |
| `BP003` | **WARNING** | Função com mais de 5 parâmetros |
| `BP004` | **WARNING** | Parâmetro sem anotação de tipo |
| `BP005` | **ERROR** | Constante global mutável: `LISTA = []` |

### Ruff (complexidade ciclomática — C90)

Funções com complexidade acima de **10** são bloqueadas pelo Ruff.
Complexidade = número de caminhos possíveis de execução (if, elif, for, while, try, and, or).

```python
# Complexidade 1 — OK
def soma(a: int, b: int) -> int:
    return a + b

# Complexidade 4 — OK (3 condições + 1 base)
def classify(x: int) -> str:
    if x < 0: return "negativo"
    elif x == 0: return "zero"
    else: return "positivo"

# Complexidade 11 — BLOQUEADO pelo Ruff
# → Divida em funções menores
```

---

## Cobertura de testes (80% mínimo no push)

A cobertura é verificada com **branch coverage** (`branch = true`), que é mais rigorosa que line coverage.
Branch coverage verifica se todos os caminhos de `if/else` foram testados.

```bash
# Ver cobertura atual (sem bloquear)
pytest tests/ -m "not integration" --cov=src/pr_analyzer --cov-report=term-missing

# Simular o que o pre-push vai fazer
pytest tests/ -m "not integration" --cov=src/pr_analyzer --cov-fail-under=80
```

**Isenções de cobertura:**
- `src/pr_analyzer/ui/` — testada manualmente via Streamlit
- `src/pr_analyzer/llm/client.py` — configuração de cliente externo

Para excluir uma linha específica de contagem:
```python
def funcao_sem_teste():  # pragma: no cover
    ...
```

---

## Exemplos de código que passa vs. falha

### FP001 — Loop proibido em módulo puro

```python
# ❌ BLOQUEADO (transforms/reducers.py)
def count_by_language(prs):
    result = {}
    for pr in prs:          # FP001
        result[pr.language] = result.get(pr.language, 0) + 1
    return result

# ✅ PERMITIDO
from functools import reduce
def count_by_language(prs):
    return reduce(
        lambda acc, pr: acc | {pr.language: acc.get(pr.language, 0) + 1},
        prs, {}
    )
```

### FP004 — Mutação proibida em módulo puro

```python
# ❌ BLOQUEADO (transforms/mappers.py)
def add_stats(results: list, pr: PRRecord) -> list:
    results.append(compute_stats(pr))   # FP004
    return results

# ✅ PERMITIDO
def add_stats(results: tuple, pr: PRRecord) -> tuple:
    return results + (compute_stats(pr),)
```

### FP005 — I/O proibido em módulo puro

```python
# ❌ BLOQUEADO (transforms/filters.py)
def by_state(state: str):
    print(f"Filtrando por: {state}")    # FP005 (debug-statements também bloqueia)
    with open("log.txt", "a") as f:     # FP005
        f.write(state)
    return lambda pr: pr.state == state

# ✅ PERMITIDO — I/O fica em io/ ou ui/
def by_state(state: str) -> Callable[[PRRecord], bool]:
    normalized = state.lower().strip()
    return lambda pr: pr.state == normalized
```

### BP002 — Função longa

```python
# ⚠️ AVISO (qualquer módulo src/)
def process_everything(filepath: str):   # BP002 — 45 linhas
    # ... 45 linhas de código ...
    pass

# ✅ RECOMENDADO — divida em funções menores
def load_data(filepath: str) -> Generator:
    ...  # 5 linhas

def apply_filters(data, filters) -> Iterable:
    ...  # 5 linhas

def aggregate(data) -> dict:
    ...  # 8 linhas
```

---

## Como instalar os hooks

```bash
# Uma vez por máquina / ambiente
make setup
# equivalente a:
pip install -e ".[dev]"
pre-commit install          # instala hooks no git commit
pre-commit install --hook-type pre-push  # instala hooks no git push
```

## Como pular um hook pontualmente (use com cautela)

```bash
# Pular apenas um hook específico
SKIP=check-paradigm git commit -m "..."

# Pular todos os hooks (raramente justificável)
git commit --no-verify -m "..."
```

Pular hooks deve ser exceção, não regra. Qualquer bypass deve ser justificado no PR.
