# Arquitetura — GitHub PR Analyzer

## Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                        UI (Streamlit)                        │
│              visualizações · filtros · exportação            │
└────────────────────────┬────────────────────────────────────┘
                         │ consome resultados
┌────────────────────────▼────────────────────────────────────┐
│                    Pipeline (HOFs)                           │
│         compose() · build_pipeline() · lazy streams          │
└──────┬──────────────────────────────────────┬───────────────┘
       │ dados puros                           │ classifica (efeito colateral)
┌──────▼──────────┐                  ┌────────▼──────────────┐
│   Transforms    │                  │   LLM + Cache         │
│  filter/map/    │                  │  Agno + Groq          │
│  reduce (puras) │                  │  hashlib + lru_cache  │
└──────┬──────────┘                  └───────────────────────┘
       │
┌──────▼──────────┐
│    I/O Layer    │
│ generators CSV  │
│ exporters       │
└─────────────────┘
```

## Módulos e Responsabilidades

| Módulo | Dev | Tipo | Responsabilidade |
|---|---|---|---|
| `src/pr_analyzer/io/` | dev1 | Efeito colateral | Leitura lazy do CSV via geradores; exportação CSV/JSON |
| `src/pr_analyzer/transforms/` | dev2 | **Puro** | `filter()`, `map()`, `reduce()` sobre PRRecords |
| `src/pr_analyzer/llm/` | dev3 | Efeito colateral | Chamadas Agno/Groq para classificação semântica |
| `src/pr_analyzer/cache/` | dev4 | Misto | `hashlib` + `lru_cache` + persistência JSON em disco |
| `src/pr_analyzer/pipeline/` | dev4 | **Puro** | `compose()`, `build_pipeline()`, HOFs de orquestração |
| `src/pr_analyzer/ui/` | dev5 | Efeito colateral | Streamlit: upload, filtros, gráficos, download |

## Regra de Isolamento: Puro vs. Efeito Colateral

```
PURO (sem I/O, sem rede, sem estado global):
  transforms/   →  filters.py · mappers.py · reducers.py
  pipeline/     →  builder.py (compose, build_pipeline)

EFEITO COLATERAL (isolado nestes módulos):
  io/           →  leitura de arquivo, escrita de arquivo
  llm/          →  chamadas HTTP ao Groq
  cache/        →  leitura/escrita do cache JSON em disco
  ui/           →  interação com usuário via Streamlit
```

O pre-commit hook `no-imperative-loops` bloqueia `for`/`while` em `transforms/` e `pipeline/`.

## Estrutura de Branches

```
main                ← protegido, só aceita PR revisado
├── dev/dev1        ← módulo io/
├── dev/dev2        ← módulo transforms/
├── dev/dev3        ← módulo llm/
├── dev/dev4        ← módulos cache/ e pipeline/
└── dev/dev5        ← módulo ui/ + infra de testes
```

**Regras:**
- Commits até **domingo 23:59** para contar na verificação semanal
- Cada dev trabalha exclusivamente no seu branch
- PR para `main` exige aprovação de 1 colega

## Ambiente de Desenvolvimento (Docker)

```bash
cp .env.example .env        # configura GROQ_API_KEY
make setup                   # instala deps + pre-commit (sem Docker)
make docker-build            # constrói imagem
make docker-run              # sobe Streamlit em localhost:8501
make docker-test             # roda testes no container
```

Todos os devs usam a mesma imagem `python:3.11-slim` para garantir paridade de ambiente.

## Fluxo TDD por Fase

```
1. Escreve teste (RED) → implementa mínimo (GREEN) → refatora (REFACTOR)
2. git commit → pre-commit hooks rodam (ruff, mypy, loop-check)
3. git push → pytest roda (pre-push hook) + CI no GitHub Actions
```

Cobertura esperada: Fase 1 → módulo do dev | Fase 2 → >50% | Fase 3 → >65% | Fase 4 → **≥80%**
