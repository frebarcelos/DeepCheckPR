# GitHub PR Analyzer

Ferramenta de análise de Pull Requests do GitHub usando paradigma funcional em Python 3.11+.

## Requisitos

- Python 3.11+
- Docker (opcional, recomendado para paridade de ambiente)
- [GROQ API Key](https://console.groq.com)

## Configuração

```bash
git clone <repo>
cd marco-2-rp3

cp .env.example .env       # preencha GROQ_API_KEY
make setup                 # instala dependências + pre-commit hooks
```

## Rodando

```bash
make run                   # Streamlit em http://localhost:8501
```

Com Docker:

```bash
make docker-build
make docker-run            # http://localhost:8501
```

## Testes

```bash
make test                  # testes unitários (sem integração)
make test-all              # todos os testes
```

## Estrutura

```
src/pr_analyzer/
├── io/          # leitura lazy do CSV (dev1)
├── transforms/  # filter/map/reduce puros (dev2)
├── llm/         # classificação via Groq (dev3)
├── cache/       # memoização com hashlib + lru_cache (dev4)
├── pipeline/    # compose() e build_pipeline() (dev4)
└── ui/          # interface Streamlit (dev5)
```

Módulos `transforms/` e `pipeline/` são **puros** — sem I/O, sem loops imperativos, sem estado mutável.
O pre-commit bloqueia violações automaticamente antes de cada commit.

## Branches

| Branch | Responsável |
|---|---|
| `dev/dev1` | módulo io/ |
| `dev/dev2` | módulo transforms/ |
| `dev/dev3` | módulo llm/ |
| `dev/dev4` | módulos cache/ e pipeline/ |
| `dev/dev5` | módulo ui/ + integração |

PRs para `main` exigem aprovação de 1 colega.
