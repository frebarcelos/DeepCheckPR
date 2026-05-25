# GitHub PR Analyzer

Ferramenta de análise de Pull Requests do GitHub usando **paradigma funcional** em Python 3.11+.

Disciplina AL0337 — Linguagens de Programação, UNIPAMPA.
5 desenvolvedores (dev1–dev5), TDD obrigatório, pre-commits rigorosos.

---

## Visão Geral

O GitAnalyzer lê datasets de Pull Requests (CSV/JSON), aplica uma cadeia de transformações funcionais puras, classifica cada PR semanticamente via LLM (Groq ou Ollama) e exibe os resultados num dashboard Streamlit interativo.

```
CSV / JSON
    │
    ▼
io/csv_reader          ← leitura lazy via generators (dev1)
    │
    ▼
transforms/            ← filter / map / reduce puros, sem I/O (dev2)
  filters.py           ← by_state, by_language, with_min_size, combine_filters
  mappers.py           ← normalize_language, normalize_state
  reducers.py          ← count_by_language, count_by_project_type, EnrichedPR
    │
    ▼
pipeline/builder.py    ← compose(), build_pipeline(), pipeline_from_env() (dev4)
    │
    ▼
cache/memo.py          ← SHA-256 + LRU + persistência JSON (dev4)
    │
    ▼
llm/classifiers.py     ← project_type / contribution_nature / clarity via Groq|Ollama (dev3)
    │
    ▼
ui/ (Streamlit)        ← upload, filtros, gráficos, export (dev5)
```

---

## Funcionalidades

| Funcionalidade | User Story | Status |
|---|---|---|
| Leitura lazy de CSV com detecção de schema | US01 | ✅ |
| Filtros por linguagem, estado, tamanho e corpo | US02 | ✅ |
| Classificação de tipo de projeto via LLM | US03 | ✅ |
| Classificação de natureza de contribuição via LLM | US04 | ✅ |
| Avaliação de clareza de descrição via LLM | US05 | ✅ |
| Gráfico de distribuição por tamanho de corpo (chars/words) | US06 | ✅ |
| Gráfico de clareza cruzada com tipo/natureza/linguagem | US07 | ✅ |
| Filtros de tipo de projeto e clareza na sidebar | US08 | ✅ |
| Cache SHA-256 + LRU com persistência JSON | RG04 | ✅ |
| Pipeline configurável por variáveis de ambiente | RG06 | ✅ |

---

## Arquitetura de Módulos

| Módulo | Dev | Tipo | Responsabilidade |
|---|---|---|---|
| `src/pr_analyzer/io/` | dev1 (Bernardo) | Efeito colateral | Leitura lazy CSV via `yield`; exportadores |
| `src/pr_analyzer/transforms/` | dev2 (Pedro) | **Puro** | `filter()`, `map()`, `reduce()` sobre PRRecords |
| `src/pr_analyzer/llm/` | dev3 (Dean) | Efeito colateral | Chamadas Agno/Groq para classificação semântica |
| `src/pr_analyzer/cache/` | dev4 (Frederico) | Misto | `hashlib` + `lru_cache` + persistência JSON |
| `src/pr_analyzer/pipeline/` | dev4 (Frederico) | **Puro** | `compose()`, `build_pipeline()`, HOFs |
| `src/pr_analyzer/ui/` | dev5 (Diogo) | Efeito colateral | Streamlit: upload, filtros, gráficos, download |

**Módulos PUROS** (`transforms/`, `pipeline/`): zero I/O, zero estado global mutável, zero loops imperativos — violações bloqueiam o commit.

---

## Requisitos

- Docker e Docker Compose
- [Groq API Key](https://console.groq.com) — para classificação LLM via nuvem
- `pipx` — para instalar o `pre-commit` no host:
  ```bash
  sudo apt install pipx && pipx ensurepath
  ```
- (Opcional) [Ollama](https://ollama.com) — para classificação LLM local, sem API key

---

## Configuração Rápida

```bash
git clone <repo>
cd marco-2-rp3

cp .env.example .env       # preencha GROQ_API_KEY e ANTHROPIC_API_KEY

make docker-build          # constrói a imagem Docker (uma vez, ~2 min)
make hooks                 # instala pre-commit e os git hooks no host (uma vez)
make docker-run            # Streamlit em http://localhost:8501
```

> **Nunca use `sudo make docker-*`** — o grupo `docker` já tem permissão e `sudo` causa conflitos de cgroup.

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `GROQ_API_KEY` | — | API key do Groq (obrigatória para backend groq) |
| `ANTHROPIC_API_KEY` | — | API key da Anthropic (hook claude-review no push) |
| `LLM_BACKEND` | `groq` | Backend LLM: `groq` ou `ollama` |
| `LLM_MODEL` | `llama3` | Modelo a usar (ex: `llama-3.1-8b-instant` para Groq, `llama3` para Ollama) |
| `OLLAMA_HOST` | `http://localhost:11434` | Host do servidor Ollama |
| `CACHE_PATH` | `.cache/llm_cache.json` | Caminho do cache persistente LLM |
| `DATASET` | — | Caminho do CSV para o pipeline CLI |
| `OUTPUT` | — | Caminho de saída JSON do pipeline CLI |
| `LIMIT` | `100` | Número máximo de registros no pipeline CLI |

---

## Backend LLM — Groq vs Ollama

### Groq (padrão — requer API key)

```bash
# .env
GROQ_API_KEY=gsk_...
LLM_BACKEND=groq
LLM_MODEL=llama-3.1-8b-instant
```

### Ollama (local — sem API key)

```bash
# 1. Instale em https://ollama.com
# 2. Baixe um modelo:
ollama pull llama3

# 3. Faça o Ollama escutar em todas as interfaces (necessário para o Docker):
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollama

# 4. Configure o .env:
LLM_BACKEND=ollama
OLLAMA_HOST=http://host.docker.internal:11434
LLM_MODEL=llama3
```

A sidebar detecta automaticamente o backend e exibe o seletor **BACKEND LLM**.

---

## Rodando

```bash
make docker-run            # dashboard Streamlit em http://localhost:8501
make docker-test           # suite de testes dentro do Docker
make docker-build          # reconstrói a imagem (após alterar dependências)

# Pipeline via CLI (sem UI):
make pipeline DATASET=data/arquivo.csv OUTPUT=out.json LIMIT=50
```

### Desenvolvimento local (sem Docker)

```bash
make setup                 # instala deps completas + hooks (Python 3.11+ necessário)
make run                   # Streamlit local
make test                  # testes unitários
```

---

## Testes

```bash
make docker-test           # roda pytest dentro do Docker com cobertura ≥80%
```

Cobertura por módulo (Sprint 4):

| Módulo | Cobertura |
|---|---|
| `transforms/` | ~95% |
| `pipeline/` | ~90% |
| `cache/` | ~85% |
| `io/` | ~80% |
| `llm/` | ~80% |
| **Total** | **≥80%** |

Os testes em `transforms/` e `pipeline/` usam **Hypothesis** para property-based testing:

```python
@given(st.text())
def test_filter_by_state_does_not_raise(state: str) -> None:
    predicate = filter_by_state(state)
    assert callable(predicate)
```

---

## Paradigma Funcional — Regras

Estas regras aplicam-se a `transforms/` e `pipeline/`. Violações **bloqueiam o commit**:

| Regra | Proibido | Alternativa |
|---|---|---|
| FP001 | Loop `for` | `map()`, `filter()`, generator expression |
| FP002 | Loop `while` | Recursão ou `itertools` |
| FP003 | `x[i] = y` (mutação por índice) | `dict \| {k: v}` ou nova tupla |
| FP004 | `.append()`, `.update()`, `.pop()` | `list + [x]`, `frozenset \| {x}` |
| FP005 | `open()`, `print()` fora de `io/` ou `ui/` | Isolar nos módulos de efeito colateral |

### Exemplos de código funcional

```python
# pipeline/builder.py — compose sem loops
def compose(*fns: Callable) -> Callable:
    return reduce(lambda f, g: lambda x: g(f(x)), fns, lambda x: x)

# cache/memo.py — chave SHA-256 determinística
def make_cache_key(prompt: str, model: str) -> str:
    payload = json.dumps({"prompt": prompt, "model": model}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

# transforms/reducers.py — reduce sem mutação
def count_by_language(prs: tuple[PRRecord, ...]) -> dict[str, int]:
    return reduce(
        lambda acc, pr: acc | {pr.language: acc.get(pr.language, 0) + 1},
        prs, {}
    )
```

---

## Estrutura do Projeto

```
marco-2-rp3/
├── src/pr_analyzer/
│   ├── io/              # dev1 — leitura lazy CSV, exportadores
│   ├── transforms/      # dev2 — filtros, mappers, reducers (PURO)
│   │   ├── filters.py
│   │   ├── mappers.py
│   │   └── reducers.py  # define EnrichedPR (NamedTuple canônico)
│   ├── llm/             # dev3 — classificação Groq/Ollama
│   │   ├── client.py
│   │   └── classifiers.py
│   ├── cache/           # dev4 — SHA-256 + LRU + JSON
│   │   └── memo.py
│   ├── pipeline/        # dev4 — compose, build_pipeline (PURO)
│   │   └── builder.py
│   └── ui/              # dev5 — Streamlit
│       ├── app.py
│       ├── components/
│       │   ├── charts.py
│       │   ├── kpis.py
│       │   ├── sidebar.py
│       │   └── tabs.py
│       └── utils/
│           ├── data.py
│           ├── exports.py
│           ├── pipeline_bridge.py
│           └── styles.py
├── tests/               # TDD — espelha src/
├── data/                # datasets locais (gitignored)
├── .env.example
├── Makefile
├── docker-compose.yml
└── pyproject.toml
```

---

## Pre-commit Hooks

| Hook | Quando roda | O que faz |
|---|---|---|
| `conventional-pre-commit` | commit-msg | Valida formato Conventional Commits |
| `ruff` | commit | Linting, imports, complexidade ciclomática (max=10) |
| `ruff-format` | commit | Formatação determinística |
| `mypy` | commit | Type checking estrito (`--strict`) |
| `check-paradigm` | commit | AST: loops, mutações, I/O em módulos puros |
| `debug-statements` | commit | Bloqueia `print()` e `breakpoint()` acidentais |
| `check-added-large-files` | commit | Impede commitar datasets >500 KB |
| `pytest-unit` | push | Suite completa de testes unitários |
| `coverage-check` | push | Cobertura ≥80% (branch coverage) |
| `claude-review` | push | Revisão semântica via Claude API |

### Formato de commit (Conventional Commits)

```
<tipo>(<escopo>): <descrição em minúsculas>

feat(cache): implementa make_cache_key com SHA-256
fix(io): corrige parsing de datas inválidas no CSV
test(transforms): adiciona casos de borda para by_date_range
```

---

## Branches e Fluxo de Integração

| Branch | Responsável | Módulo |
|---|---|---|
| `bernardo` | dev1 | `io/` |
| `pedro` | dev2 | `transforms/` |
| `dev/dev3` | dev3 (Dean) | `llm/` |
| `frederico-barcelos` | dev4 | `cache/`, `pipeline/` |
| `diogo` | dev5 | `ui/` |

```
feature branch → PR → develop → PR → main
```

- PRs para `main` exigem aprovação de **1 colega**
- **Nunca commitar diretamente em `develop`** — sempre via branch de dev → PR
- Push é sempre feito pelo **desenvolvedor**, nunca automatizado

---

## Cronograma

| Sprint | Verificação | Meta de Cobertura | Status |
|---|---|---|---|
| 1 — Estrutura base | 04/05/2026 | Módulo funciona | ✅ |
| 2 — Transformações | 11/05/2026 | >50% | ✅ |
| 3 — LLM + Pipeline | 18/05/2026 | >65% | ✅ |
| 4 — UI + Integração | 25/05/2026 | **≥80%** | ✅ |
| Entrega Final | 01/06/2026 | ≥80% | — |
