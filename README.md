# GitHub PR Analyzer

Ferramenta de análise de Pull Requests do GitHub usando paradigma funcional em Python 3.11+.

## Requisitos

- Docker e Docker Compose
- [GROQ API Key](https://console.groq.com)
- `pipx` — para instalar o `pre-commit` no host sem poluir o Python do sistema:
  ```bash
  sudo apt install pipx && pipx ensurepath
  # abra um novo terminal após rodar o comando acima
  ```

## Configuração

```bash
git clone <repo>
cd marco-2-rp3

cp .env.example .env       # preencha GROQ_API_KEY e ANTHROPIC_API_KEY

make docker-build          # constrói a imagem (uma vez, ~2 min)
make hooks                 # instala pre-commit e os git hooks no host (uma vez)
```

O `make hooks` instala apenas o binário `pre-commit` via pipx — **não instala o ambiente Python completo**.
Os hooks de commit (ruff, mypy, check-paradigm) rodam em ambientes isolados gerenciados pelo próprio pre-commit.
Os hooks de push (pytest, cobertura, claude-review) executam **dentro do container Docker**.

## Rodando

```bash
make docker-run            # Streamlit em http://localhost:8501
```

## Testes

```bash
make docker-test           # roda a suite de testes dentro do Docker
```

## Fluxo de trabalho

```
edita código  →  git commit  →  hooks de commit rodam (ruff, mypy, check-paradigm)
                                  ↓ falhou? corrija e tente de novo
              →  usuário dá push  →  hooks de push rodam via Docker (pytest, coverage)
                                  ↓ falhou? corrija, commita, tenta de novo
```

> **Push é sempre feito pelo desenvolvedor**, nunca automatizado. Hooks de push precisam que o Docker esteja rodando.

## Desenvolvimento sem Docker (alternativa)

Para rodar tudo localmente sem Docker:

```bash
make setup                 # instala todas as deps + hooks (Python 3.11+ necessário)
make run                   # Streamlit em http://localhost:8501
make test                  # testes unitários
```

## Estrutura

```
src/pr_analyzer/
├── io/          # leitura lazy do CSV (dev1)
├── transforms/  # filter/map/reduce puros (dev2)
├── llm/         # classificação via Groq/Ollama (dev3)
├── cache/       # memoização com hashlib + lru_cache (dev4)
├── pipeline/    # compose() e build_pipeline() (dev4)
└── ui/          # interface Streamlit (dev5)
```

Módulos `transforms/` e `pipeline/` são **puros** — sem I/O, sem loops imperativos, sem estado mutável.
O pre-commit bloqueia violações automaticamente antes de cada commit.

## Branches

| Branch | Responsável |
|---|---|
| `bernardo` | módulo io/ |
| `pedro` | módulo transforms/ |
| `dev/dev3` | módulo llm/ |
| `frederico-barcelos` | módulos cache/ e pipeline/ |
| `diogo` | módulo ui/ + integração |

PRs para `main` exigem aprovação de 1 colega.
