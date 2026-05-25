# CLAUDE.md — GitHub PR Analyzer

## Identidade do Projeto

Ferramenta de análise de Pull Requests do GitHub usando **paradigma funcional** em Python 3.11+.
Disciplina AL0337 — Linguagens de Programação, UNIPAMPA, Sprint 3 concluída (2026-05-18), Sprint 4 em andamento.
5 desenvolvedores (dev1–dev5), TDD obrigatório, pre-commits rigorosos.

## Arquitetura de Módulos

| Módulo | Dev | Tipo | O que faz |
|---|---|---|---|
| `src/pr_analyzer/io/` | dev1 | Efeito colateral | Leitura lazy do CSV via geradores; exportadores |
| `src/pr_analyzer/transforms/` | dev2 | **PURO** | `filter()`, `map()`, `reduce()` sobre PRRecords |
| `src/pr_analyzer/llm/` | dev3 | Efeito colateral | Chamadas Agno/Groq para classificação semântica |
| `src/pr_analyzer/cache/` | dev4 | Misto | `hashlib` + `lru_cache` + persistência JSON |
| `src/pr_analyzer/pipeline/` | dev4 | **PURO** | `compose()`, `build_pipeline()`, HOFs |
| `src/pr_analyzer/ui/` | dev5 | Efeito colateral | Streamlit: upload, filtros, gráficos, download |

**Módulos PUROS** (`transforms/`, `pipeline/`): zero I/O, zero estado global mutável, zero loops imperativos.
**Módulos de EFEITO COLATERAL** (`io/`, `llm/`, `cache/`, `ui/`): únicos lugares onde I/O é permitido.

## Regras de Paradigma Funcional (OBRIGATÓRIO)

### Em `transforms/` e `pipeline/` — Violações bloqueiam o commit:

| Regra | Proibido | Alternativa |
|---|---|---|
| FP001 | Loop `for` | `map()`, `filter()`, generator expression, `itertools` |
| FP002 | Loop `while` | Recursão ou `itertools` |
| FP003 | `x[i] = y` (mutação por índice) | `dict \| {k: v}` ou nova tupla |
| FP004 | `.append()`, `.update()`, `.pop()`, etc. | `list + [x]`, `frozenset \| {x}` |
| FP005 | `open()`, `.write()`, `print()` | Isolar em `io/` |
| FP006 | `LISTA = []` em escopo de módulo | `frozenset`, `tuple` |

### Em todos os arquivos `src/` — Avisos (não bloqueiam):

| Regra | O que verifica |
|---|---|
| BP001 | Função pública sem anotação `-> tipo` |
| BP002 | Função com mais de 30 linhas |
| BP003 | Função com mais de 5 parâmetros |
| BP004 | Parâmetro sem anotação de tipo |
| BP005 | Constante global mutável (ex: `LISTA = []`) — bloqueia |

## Padrões de Código

### Estrutura de funções puras (transforms/)
```python
from functools import reduce
from typing import Callable

def filter_by_state(state: str) -> Callable[[PRRecord], bool]:
    normalized = state.lower().strip()
    return lambda pr: pr.state == normalized

def count_by_language(prs: tuple[PRRecord, ...]) -> dict[str, int]:
    return reduce(
        lambda acc, pr: acc | {pr.language: acc.get(pr.language, 0) + 1},
        prs, {}
    )
```

### Estrutura de tipos imutáveis
```python
from typing import NamedTuple

class PRRecord(NamedTuple):
    id: int
    title: str
    state: str
    language: str
    # ... demais campos
```

### Estrutura de testes (TDD)
```python
import pytest
from hypothesis import given, strategies as st

def test_filter_by_state_returns_only_open(sample_prs: tuple) -> None:
    result = tuple(filter(filter_by_state("open"), sample_prs))
    assert all(pr.state == "open" for pr in result)

@given(st.text())
def test_filter_by_state_does_not_raise(state: str) -> None:
    predicate = filter_by_state(state)
    assert callable(predicate)
```

## Estrutura de Branches

```
main               ← protegido, só aceita PR revisado por 1 colega
develop            ← integração entre sprints
├── bernardo       ← módulo io/  (dev1)
├── pedro          ← módulo transforms/  (dev2)
├── dev/dev3       ← módulo llm/  (dev3/Dean)
├── frederico-barcelos ← módulos cache/ e pipeline/  (dev4)
└── diogo          ← módulo ui/ + integração  (dev5)
```

- Commits até **domingo 23:59** para a verificação semanal
- PR para `main` exige aprovação de 1 colega

## Cronograma de Fases

| Fase | Verificação | Meta de Cobertura | Status |
|---|---|---|---|
| 1 — Estrutura base | 04/05/2026 | Módulo do dev funciona | ✅ Concluída |
| 2 — Transformações | 11/05/2026 | >50% | ✅ Concluída |
| 3 — LLM + Pipeline | 18/05/2026 | >65% | ✅ Concluída |
| 4 — UI + Integração | 25/05/2026 | **≥80%** | 🔄 Em andamento |
| Entrega Final | 01/06/2026 | ≥80% | — |

## Padrão de Mensagem de Commit (OBRIGATÓRIO)

Todo commit deve seguir o formato **Conventional Commits**. O hook `conventional-pre-commit` bloqueia qualquer commit que não siga o padrão.

```
<tipo>(<escopo opcional>): <descrição curta em minúsculas>
```

### Tipos permitidos

| Tipo | Quando usar |
|------|-------------|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `test` | Adição ou correção de testes |
| `docs` | Documentação |
| `chore` | Manutenção, configs, dependências |
| `refactor` | Refatoração sem mudança de comportamento |
| `style` | Formatação, espaçamento (sem lógica) |
| `perf` | Melhoria de performance |
| `ci` | CI/CD e pipelines |
| `build` | Sistema de build, Docker, Makefile |
| `revert` | Reverter commit anterior |

### Exemplos válidos

```
feat(cache): implementa make_cache_key com SHA-256
fix(io): corrige parsing de datas inválidas no CSV
test(transforms): adiciona casos de borda para by_date_range
chore(deps): atualiza streamlit para 1.35
refactor(pipeline): simplifica compose usando functools.reduce
```

### Exemplos inválidos (serão bloqueados)

```
update stuff          ← sem tipo
Feat: nova função     ← tipo com maiúscula
feat: .               ← descrição vazia
fixed bug             ← sem tipo
```

## Pre-commit Hooks

| Hook | Quando roda | O que faz |
|---|---|---|
| `conventional-pre-commit` | commit-msg | Valida formato Conventional Commits |
| `ruff` | commit | Linting, imports, complexidade ciclomática (max=10), naming |
| `ruff-format` | commit | Formatação determinística |
| `mypy` | commit | Type checking estrito (`--strict`) |
| `check-paradigm` | commit | AST: loops, mutações, I/O em módulos puros |
| `debug-statements` | commit | Bloqueia `print()` e `breakpoint()` acidentais |
| `check-added-large-files` | commit | Impede commitar o CSV do dataset (>500KB) |
| `pytest-unit` | push | Suite completa de testes unitários |
| `coverage-check` | push | Cobertura ≥80% (branch coverage) |
| `claude-review` | push | Revisão semântica via Claude API |

## Ambiente de Desenvolvimento

**Docker é o ambiente primário.** Instale apenas o necessário no host:

```bash
cp .env.example .env     # configure GROQ_API_KEY e ANTHROPIC_API_KEY
make docker-build        # constrói imagem Docker (uma vez; NUNCA use sudo)
make hooks               # instala pre-commit + git hooks no host (uma vez, mínimo)
make docker-run          # Streamlit em localhost:8501
make docker-test         # testes unitários dentro do Docker
make pipeline DATASET=data/arquivo.json OUTPUT=out.json LIMIT=20  # pipeline via CLI
```

Para desenvolvimento sem Docker (alternativo):
```bash
make setup               # instala deps completas + hooks
make run                 # Streamlit local
make test                # testes unitários locais
```

Imagem base: `python:3.11-slim`. Hooks de push rodam via Docker automaticamente.

### Backend LLM — Groq vs Ollama

Por padrão o projeto usa Groq (requer `GROQ_API_KEY`). Para usar Ollama local (sem API key):

```bash
# No .env:
LLM_BACKEND=ollama
OLLAMA_HOST=http://host.docker.internal:11434   # dentro do Docker no Linux
LLM_MODEL=llama3                                # modelo instalado via ollama pull

# No host (uma vez):
# 1. Instale em https://ollama.com
# 2. ollama pull llama3
# 3. Faça o Ollama escutar em todas as interfaces (necessário para o Docker alcançar):
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

A UI detecta automaticamente o backend configurado no `.env` e exibe o seletor **BACKEND LLM** na sidebar.

### Dataset local na UI

A sidebar exibe automaticamente os arquivos encontrados em `data/`:
- Arquivos CSV/JSON no nível raiz
- Arquivos do archive `data/archive/` (formato mined-comments por linguagem)

Para os archives (6–11 GB por linguagem), o carregamento usa streaming via `ijson` e retorna uma amostra de 2.000 comentários. A classificação `nature`/`clarity` nessa amostra é heurística (palavras-chave + tamanho do corpo) — a integração com LLM real é tarefa futura da Sprint 4 (dev4 + dev5).

## Hierarquia de Importações (OBRIGATÓRIO)

Para evitar imports circulares, respeite estritamente a direção das dependências:

```
io/csv_reader  ←  transforms/mappers  ←  transforms/reducers
                                               ↑
                                        pipeline/builder (re-exporta EnrichedPR)
                                               ↑
                                         cache/memo
                                               ↑
                                         llm/classifiers
                                               ↑
                                          ui/utils/
```

**Regras derivadas:**
- `transforms/` **nunca** importa de `pipeline/`, `cache/`, `llm/` ou `ui/`
- `pipeline/` **nunca** importa de `cache/`, `llm/` ou `ui/`
- `cache/` **nunca** importa de `llm/` ou `ui/`

### `EnrichedPR` — localização canônica

`EnrichedPR` é definido **somente** em `src/pr_analyzer/transforms/reducers.py` como `NamedTuple`. Todos os outros módulos importam de lá:

```python
# CORRETO — em pipeline/, cache/, llm/, ui/:
from pr_analyzer.transforms.reducers import EnrichedPR
# ou via re-exportação do pipeline:
from pr_analyzer.pipeline.builder import EnrichedPR

# ERRADO — nunca redefina EnrichedPR como @dataclass ou NamedTuple local
```

Motivo: definir `EnrichedPR` em `pipeline/builder` e importar de `transforms/reducers` (que já importa de `pipeline/builder`) cria import circular. A ordem correta é `reducers` define → `builder` importa.

### Aliases em inglês em `classifiers.py`

`classifiers.py` expõe aliases em inglês no final do arquivo para compatibilidade com `pipeline_bridge.py` e outros módulos:

```python
classify_project_type = classificar_tipo_projeto
classify_contribution_nature = classificar_natureza_contribuicao
classify_description_clarity = avaliar_clareza_descricao
```

Qualquer nova função em `llm/classifiers.py` deve ter tanto o nome em português quanto o alias em inglês.

### BP005 se aplica a `ui/` também

Constantes globais mutáveis (`dict`, `list`) bloqueiam o commit em **todos** os arquivos `src/`, incluindo `ui/`. Use funções retornando o valor ou `tuple`/`frozenset`:

```python
# ERRADO — bloqueia mesmo em ui/:
_CHART_CFG = {"displayModeBar": False}

# CORRETO:
def _chart_cfg() -> dict[str, bool]:
    return {"displayModeBar": False}
```

### `st.cache_data` e mypy strict

O decorator `@st.cache_data` não tem stubs completos e causa `error: Untyped decorator makes function ... untyped [misc]`. Use:

```python
@st.cache_data(show_spinner=False)  # type: ignore[misc]
def get_mock_data() -> pd.DataFrame:
```

## Protocolo de Merge Entre Sprints (OBRIGATÓRIO)

Ao final de cada sprint, o fluxo de integração é:

1. **Cada branch de dev → `develop`** (via PR no GitHub, sem fast-forward)
2. **`develop` → cada branch de dev** (para distribuir o código integrado de volta)

### Regra crítica de commits em `develop`

**Nunca commitar diretamente em `develop`.** Se surgir qualquer ajuste necessário durante o processo de merge (conflitos, correções, adaptações):

1. Fazer a alteração na branch `frederico-barcelos`
2. Commitar e fazer push de `frederico-barcelos`
3. Abrir PR de `frederico-barcelos` → `develop`
4. Só então continuar o merge das outras branches

### Ordem de merge recomendada (menor → maior risco de conflito)

```
bernardo           → develop   (io/ — leitura CSV, isolado)
pedro              → develop   (transforms/ — funções puras, isolado)
dev/dev3           → develop   (llm/ — módulo próprio)
frederico-barcelos → develop   (cache/ + pipeline/ — integra com transforms)
diogo              → develop   (ui/ — depende de todos os anteriores)
```

O PR do Diogo deve ser aberto **somente após** os de Bernardo, Pedro e Dean, porque o `pipeline_bridge.py` tem `try/except ImportError` que resolve para as implementações reais quando elas estão em `develop`.

Após todos em `develop`:
```
develop → bernardo
develop → pedro
develop → dev/dev3
develop → frederico-barcelos
develop → diogo
```

### Verificação pós-merge

Depois que todos os PRs entrarem em `develop`:
```bash
make docker-test   # confirma que imports, testes e cobertura passam com o código integrado
```

Erros comuns de integração e suas correções:
- **Import circular** → verifique a hierarquia de importações acima; `transforms/` nunca deve importar de `pipeline/`
- **Tipo incompatível com `EnrichedPR`** → confirme que todos usam `from pr_analyzer.transforms.reducers import EnrichedPR`
- **Conflito de merge não resolvido** → verifique conflict markers com `grep -rn "<<<<<<" src/`
- **BP005 em `ui/`** → dicts e lists globais viram funções

## Regras de Commit e Push (OBRIGATÓRIO)

### Para commits
- **Nunca commitar se os pre-commit hooks não estiverem instalados.** Verifique com `ls .git/hooks/pre-commit` — se o arquivo não existir (apenas `.sample`), execute `make setup` antes de qualquer commit.
- **Nunca commitar se o pre-commit não passar.** Qualquer falha em ruff, mypy, check-paradigm ou conventional-pre-commit bloqueia o commit até ser corrigida.

### Para push
- **Push e merge de PRs são operações do desenvolvedor.** O assistente cria commits locais e pode abrir PRs via `gh`, mas `git push` e `gh pr merge` requerem autorização explícita do desenvolvedor para cada sessão.

## O que NUNCA fazer

- **Nunca** usar `for` ou `while` em `transforms/` ou `pipeline/`
- **Nunca** chamar `.append()`, `.update()` ou qualquer método mutante em módulos puros
- **Nunca** colocar `open()` ou `print()` fora de `io/` ou `ui/`
- **Nunca** commitar o arquivo CSV ou os archives JSON de `data/` (estão no .gitignore)
- **Nunca** deletar `.dockerignore` — ele exclui os 28 GB de `data/archive/` do build context
- **Nunca** usar `sudo make docker-*` — o grupo `docker` já tem permissão e sudo causa conflitos de cgroup irrecuperáveis
- **Nunca** criar implementação sem escrever o teste antes (TDD)
- **Nunca** fazer push direto para `main` (branch protegida)
- **Nunca** commitar diretamente em `develop` — sempre via `frederico-barcelos` → PR → `develop`
- **Nunca** commitar com hooks inativos ou com pre-commit falhando
- **Nunca** executar `git push` — push é sempre feito pelo usuário

## Ao Revisar Código Neste Projeto

1. Verifique se a função pertence ao módulo correto (puro vs efeito colateral)
2. Confirme que existe teste antes da implementação (TDD)
3. Valide anotações de tipo em todas as assinaturas públicas
4. Prefira `NamedTuple` ou `frozenset` para estruturas de dados
5. Funções devem ter no máximo 30 linhas e 5 parâmetros
6. Use `map()`, `filter()`, `reduce()` em vez de loops em módulos puros
