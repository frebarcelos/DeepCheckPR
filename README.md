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
  heuristics.py        ← pré-classificação por keywords (sem LLM)
    │
    ▼
pipeline/builder.py    ← compose(), build_pipeline(), pipeline_from_env() (dev4)
    │
    ▼
cache/memo.py          ← SHA-256 + LRU + persistência JSON ou SQLite (dev4)
cache/sqlite_store.py  ← SqliteKVStore WAL + thread-safe (dev4)
    │
    ▼
llm/classifiers.py     ← enrich_prs async/batch/tools via Groq|Ollama (dev3)
llm/client.py          ← HTTP keep-alive, retry com backoff exponencial
llm/metrics.py         ← ClassificationMetrics: throughput, fallback rate
llm/system_probe.py    ← auto-detecção CPU/RAM/GPU → PipelineConfig ideal
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
| Heurísticas de pré-classificação (sem LLM) | LLM-04 | ✅ |
| Cliente async + batch + retry com backoff | LLM-01/02/07 | ✅ |
| HTTP keep-alive por thread | LLM-03 | ✅ |
| Cache SQLite persistente entre containers | LLM-10 | ✅ |
| Métricas de throughput e fallback rate | LLM-06 | ✅ |
| Auto-detecção de hardware (CPU/RAM/GPU) | system_probe | ✅ |
| **Result-cache cross-sessão**: PR já classificado não é reclassificado | v6 | ✅ |
| **Seletor de escala** com estimativas de tempo (500/2k/10k/50k) | v6 | ✅ |
| **"Todas as bases"**: carrega e concatena todos os datasets em data/ | v6 | ✅ |
| **`pipeline-all`**: processa dataset completo sem limite via CLI | v6 | ✅ |
| **Complexidade de revisão** (`review_complexity`): low/medium/high por PR | v7 | ✅ |
| **Guardrails de entrada**: `sanitize` + `validate_pr` rejeitam PRs corrompidos antes do LLM | v7 | ✅ |

---

## Arquitetura de Módulos

| Módulo | Dev | Tipo | Responsabilidade |
|---|---|---|---|
| `src/pr_analyzer/io/` | dev1 (Bernardo) | Efeito colateral | Leitura lazy CSV via `yield`; exportadores |
| `src/pr_analyzer/transforms/` | dev2 (Pedro) | **Puro** | `filter()`, `map()`, `reduce()`; `heuristics.py` (keywords) |
| `src/pr_analyzer/llm/` | dev3 (Dean) | Efeito colateral | Groq/Ollama async+batch+tools; `metrics.py`; `system_probe.py` |
| `src/pr_analyzer/cache/` | dev4 (Frederico) | Misto | `hashlib` + LRU JSON; `sqlite_store.py` WAL persistente |
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
| **Otimizações de throughput** | | |
| `LLM_MAX_WORKERS` | `auto` | Threads paralelas (`auto` detecta hardware, número fixo sobrescreve) |
| `LLM_USE_TOOLS` | `false` | Tool calling: 1 chamada/PR em vez de 3 (requer modelo compatível) |
| `LLM_BATCH_SIZE` | `1` | PRs por chamada batch (5–10 com `qwen2:1.5b`, 1 = individual) |
| `LLM_MAX_RETRIES` | `3` | Tentativas de retry em falha de conexão |
| `LLM_RETRY_BASE_DELAY` | `1.0` | Delay base do backoff exponencial (segundos) |
| `LLM_BODY_CHARS_SINGLE` | `400` | Caracteres do body em chamadas individuais |
| `LLM_BODY_CHARS_BATCH` | `100` | Caracteres do body em chamadas batch (prompt compacto) |

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

Cobertura por módulo (v7.0.0 — 2026-05-30):

| Módulo | Cobertura |
|---|---|
| `transforms/` | ~100% |
| `pipeline/` | ~100% |
| `cache/` | ~100% |
| `io/` | ~100% |
| `llm/classifiers.py` | ~94% |
| `llm/metrics.py` | 100% |
| `llm/system_probe.py` | ~39% (I/O — mockado intencionalmente) |
| **Total** | **89%** |

Os testes em `transforms/` e `pipeline/` usam **Hypothesis** para property-based testing:

```python
@given(st.text())
def test_filter_by_state_does_not_raise(state: str) -> None:
    predicate = filter_by_state(state)
    assert callable(predicate)
```

---

## Otimizações de Performance (Sprint 5 + v6)

O pipeline com `llama3` (4.7 GB) processava ~2000 PRs em **~5h** sequencialmente.
Após as otimizações com `qwen2:1.5b` + todas as flags ativas: **~12 min**.
Com result-cache SQLite (v6): execuções repetidas nos mesmos dados → **instantâneo**.

| Otimização | Módulo | Ganho |
|---|---|---|
| Async HTTP (`asyncio.gather`) | `llm/classifiers.py` | 2–4× throughput |
| Adaptive batch size | `llm/classifiers.py` | Elimina fallbacks caros |
| HTTP keep-alive por thread | `llm/client.py` | 5–15% latência |
| Heurísticas de pré-classificação | `transforms/heuristics.py` | 10–30% chamadas eliminadas |
| Cache de tipo por repositório | `llm/classifiers.py` | ~33% menos tokens |
| Prompt compression (body truncado) | `llm/classifiers.py` | 10–20% menos tokens |
| Retry com backoff exponencial | `llm/client.py` | Resiliência a timeouts |
| SQLite cache persistente (WAL) | `cache/sqlite_store.py` | Cache sobrevive ao Docker rebuild |
| Auto-detecção de hardware | `llm/system_probe.py` | Workers/batch ajustados ao hardware |
| Métricas de observabilidade | `llm/metrics.py` | Throughput, fallback rate em tempo real |
| **Result-cache cross-sessão** | `llm/classifiers.py` | PRs já classificados: 0 chamadas LLM |

### Configuração recomendada para máxima velocidade (Ollama)

```bash
LLM_BACKEND=ollama
LLM_MODEL=qwen2:1.5b        # ollama pull qwen2:1.5b
LLM_MAX_WORKERS=auto         # detecta CPU/RAM/GPU automaticamente
LLM_USE_TOOLS=true
LLM_BATCH_SIZE=5
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
│   │   ├── client.py        # HTTP keep-alive, retry backoff, async
│   │   ├── classifiers.py   # enrich_prs async/batch/tools/heuristics
│   │   ├── metrics.py       # ClassificationMetrics: throughput, fallbacks
│   │   ├── skills.py        # system prompt + few-shot examples
│   │   └── system_probe.py  # auto-detecção CPU/RAM/GPU → PipelineConfig
│   ├── cache/           # dev4 — SHA-256 + LRU + JSON/SQLite
│   │   ├── memo.py          # cached_classify + make_enriched_classifier
│   │   └── sqlite_store.py  # SqliteKVStore WAL thread-safe
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
| 5 — Otimizações LLM | 26/05/2026 | ≥80% | ✅ (87%) |
| 6 — Persistência + UI | 26/05/2026 | ≥80% | ✅ (88%) |
| 7 — Integração Gift | 30/05/2026 | ≥80% | ✅ (89%) |
| Entrega Final (Marco 02) | 01/06/2026 | ≥80% | — |
