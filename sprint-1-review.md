# Sprint 1 Review — dev4

**Período:** 01/05/2026 → 04/05/2026
**Branch:** `frederico-barcelos`
**Verificação:** 04/05/2026

---

## Estrutura estabelecida

Além das tasks de implementação, esta sprint consolidou a base do projeto inteiro:

| Entrega | O que é |
|---|---|
| `Dockerfile` + `docker-compose.yml` | Ambiente Python 3.11-slim idêntico para todos os devs |
| `.pre-commit-config.yaml` | Hooks automáticos: ruff, mypy, paradigma funcional, cobertura, revisão local |
| `scripts/check_paradigm.py` | Verificador AST — bloqueia loops e mutações em módulos puros no commit |
| `scripts/claude_review.py` | Revisão de código local no pre-push sem custo de API |
| `pyproject.toml` | Build backend corrigido, `pythonpath = ["src"]` no pytest |
| `CLAUDE.md` | Especificações completas lidas automaticamente pelo Claude Code |
| `.claude/local/dev4.md` | Contexto pessoal do dev4 por sprint (gitignored) |
| `src/pr_analyzer/ui/app.py` | Placeholder Streamlit para o container subir |
| `README.md` | Instruções de setup e execução do projeto |
| `plano/fase-1.md` a `fase-4.md` | 50 tasks divididas por dev e fase |

Correções encontradas durante a sprint:
- `.gitignore`: `cache/` → `/cache/` (estava ignorando `src/pr_analyzer/cache/`)
- `pyproject.toml`: build backend `setuptools.backends.legacy` não existe no Python 3.11-slim

---

## Tasks implementadas

### TASK-10 — `make_cache_key` ✅

**Arquivo:** `src/pr_analyzer/cache/memo.py`
**Testes:** `tests/test_cache/test_memo.py` (5 testes)

Função pura que gera chave SHA-256 determinística a partir de argumentos variáveis.

Detalhe encontrado na refatoração: separador `:` causava colisão entre argumentos
(`make_cache_key("a:b", "c") == make_cache_key("a", "b:c")`). Corrigido com separador
nulo `\x00`, adicionando um 5º teste que detecta e previne regressão.

```python
make_cache_key("123", "llama3")  # → "b0ee04f880c4ff42"
make_cache_key("456", "llama3")  # → hash diferente
```

**Cobertura:** 100% (branch coverage)

---

### TASK-11 — `cached_classify` ✅

**Arquivo:** `src/pr_analyzer/cache/memo.py`
**Testes:** `tests/test_cache/test_cached_classify.py` (4 testes)

HOF que envolve qualquer função classificadora evitando chamadas repetidas.
LRU manual via `OrderedDict` com limite configurável. Persistência opcional em JSON.

```python
wrapped = cached_classify(groq_classify, cache_size=1024, cache_path=Path("cache/llm.json"))
wrapped("repo", "Fix bug")   # chama groq_classify
wrapped("repo", "Fix bug")   # retorna do cache — groq não é chamado
```

Sobrevive a reinicialização do processo se `cache_path` for fornecido.

**Cobertura:** 100% (branch coverage)

---

### TASK-12 — Esqueleto do pipeline builder ✅

**Arquivo:** `src/pr_analyzer/pipeline/builder.py`
**Testes:** `tests/test_pipeline/test_builder.py` (6 testes)

Assinaturas completas com tipos para `compose()`, `pipe()` e `build_pipeline()`.
Implementações levantam `NotImplementedError` — serão desenvolvidas na sprint 2.

```python
def compose(*fns: Callable) -> Callable: ...
def pipe(value: T, *fns: Callable) -> T: ...
def build_pipeline(*steps: Callable) -> Callable: ...
```

---

## Cobertura de testes

```
src/pr_analyzer/cache/memo.py     100%  (branch coverage)
src/pr_analyzer/pipeline/builder.py  —  (stubs, implementação na sprint 2)
```

Meta da sprint 1: módulo do dev funciona ✅

---

## Vale a pena QA por outro dev?

**TASK-10 e TASK-11 — sim, QA faz sentido.**

Os testes cobrem 100% do código e os casos de borda relevantes (colisão de chave,
persistência entre instâncias). Mas um segundo par de olhos pode agregar ao revisar:

- Se o comportamento de eviction do LRU está correto quando `cache_size` é atingido
- Se a persistência JSON é suficiente ou se deveria ser atômica (write + rename)
- Se `cache_path=None` como padrão é uma boa API ou deveria sempre persistir

Esses são julgamentos de design que os testes não capturam.

**TASK-12 — não precisa de QA agora.**

É apenas um esqueleto de interface. O QA real acontece na sprint 2, quando
`compose()` e `build_pipeline()` tiverem implementação de verdade e os testes
testarem comportamento, não só `NotImplementedError`.

**Recomendação:** mover TASK-10 e TASK-11 para **Done com revisão** e TASK-12
para **Done** direto — ela só estará realmente pronta ao fim da sprint 2.
