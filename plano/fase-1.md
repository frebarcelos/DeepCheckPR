# Fase 1 — Fundação

**Verificação semanal:** 04/05/2026
**Critério de TOk:** leitura lazy do CSV funcionando, pelo menos 1 filtro puro com teste passando, ambiente Docker configurado.

---

## dev1 — Módulo `io/`

### TASK-01 — Criar modelo de dados PRRecord
- **O que fazer:** Definir `PRRecord` como `NamedTuple` com os campos do dataset Kaggle: `pr_id`, `repo_name`, `language`, `title`, `body`, `state`, `created_at`, `merged_at`, `additions`, `deletions`, `changed_files`.
- **Arquivo:** `src/pr_analyzer/io/csv_reader.py`
- **Entrega:** classe definida + teste verificando imutabilidade (`result.pr_id = "x"` levanta `AttributeError`)
- **Label:** `fase-1` `dev1` `io` `tdd`

### TASK-02 — Implementar leitura lazy do CSV com gerador
- **O que fazer:** Função `read_csv_lazy(filepath: str) -> Generator[dict, None, None]` que usa `csv.DictReader` e `yield from`. Não deve carregar o CSV inteiro em memória.
- **Arquivo:** `src/pr_analyzer/io/csv_reader.py`
- **Entrega:** função + teste que confirma retorno de `GeneratorType` e leitura linha a linha
- **Label:** `fase-1` `dev1` `io` `tdd`

### TASK-03 — Implementar normalização de schema
- **O que fazer:** Função pura `apply_schema(raw_row: dict) -> PRRecord` que converte dict bruto do CSV em `PRRecord`, normalizando tipos (`int` para additions/deletions, `str.lower()` para language) com fallback para campos ausentes.
- **Arquivo:** `src/pr_analyzer/io/csv_reader.py`
- **Entrega:** função + testes para campo ausente, tipo inválido, language em maiúsculo
- **Label:** `fase-1` `dev1` `io` `tdd`

### TASK-04 — Implementar pipeline completo `read_prs()`
- **O que fazer:** Função `read_prs(filepath: str) -> Generator[PRRecord, None, None]` que compõe `read_csv_lazy` + `apply_schema` em expressão geradora: `(apply_schema(row) for row in read_csv_lazy(filepath))`.
- **Arquivo:** `src/pr_analyzer/io/csv_reader.py`
- **Entrega:** função + teste confirmando que retorna gerador de `PRRecord`
- **Label:** `fase-1` `dev1` `io` `tdd`

---

## dev2 — Módulo `transforms/`

### TASK-05 — Implementar filtros por estado e linguagem
- **O que fazer:** Funções `by_state(state: str)` e `by_language(language: str)` que retornam predicados `Callable[[PRRecord], bool]`. Devem ser case-insensitive e sem efeitos colaterais.
- **Arquivo:** `src/pr_analyzer/transforms/filters.py`
- **Entrega:** funções + testes para match correto, mismatch e case-insensitivity
- **Label:** `fase-1` `dev2` `transforms` `tdd`

### TASK-06 — Implementar filtro por intervalo de datas
- **O que fazer:** Função `by_date_range(start: str, end: str) -> Callable[[PRRecord], bool]` comparando `pr.created_at[:10]` com strings ISO 8601.
- **Arquivo:** `src/pr_analyzer/transforms/filters.py`
- **Entrega:** função + testes para data dentro, fora e exatamente no limite do intervalo
- **Label:** `fase-1` `dev2` `transforms` `tdd`

### TASK-07 — Implementar filtros auxiliares e combinador
- **O que fazer:** Funções `with_non_empty_body()`, `with_min_size(min_changes: int)` e `combine_filters(*predicates)` (HOF que combina predicados com `all()`).
- **Arquivo:** `src/pr_analyzer/transforms/filters.py`
- **Entrega:** funções + testes, incluindo `combine_filters` com lista vazia (deve retornar `True` sempre)
- **Label:** `fase-1` `dev2` `transforms` `tdd`

---

## dev3 — Módulo `llm/`

### TASK-08 — Configurar cliente Agno + Groq
- **O que fazer:** Função `create_groq_client() -> Agent` que lê `GROQ_API_KEY` e `LLM_MODEL` do `.env` e retorna agente Agno configurado. Isolar como efeito colateral.
- **Arquivo:** `src/pr_analyzer/llm/client.py`
- **Entrega:** função + teste com mock do Agno verificando que a key é lida do ambiente
- **Label:** `fase-1` `dev3` `llm` `tdd`

### TASK-09 — Definir interface dos classificadores com stubs
- **O que fazer:** Criar as 3 funções de classificação com assinaturas completas e docstrings, mas retornando valores fixos (stubs). Isso permite que os outros devs dependam da interface antes da implementação real.
  - `classify_project_type(repo_name, sample_titles, client) -> str`
  - `classify_contribution_nature(title, body, client) -> str`
  - `classify_description_clarity(body, client) -> str`
- **Arquivo:** `src/pr_analyzer/llm/classifiers.py`
- **Entrega:** stubs + `frozenset` com valores válidos de cada classificação + testes com mock
- **Label:** `fase-1` `dev3` `llm` `tdd`

---

## dev4 — Módulos `cache/` e `pipeline/`

### TASK-10 — Implementar geração de chave de cache com hashlib
- **O que fazer:** Função pura `make_cache_key(*args: str) -> str` que gera hash SHA-256 determinístico concatenando os argumentos.
- **Arquivo:** `src/pr_analyzer/cache/memo.py`
- **Entrega:** função + testes verificando determinismo (mesma entrada = mesma saída) e unicidade (entradas diferentes = hashes diferentes)
- **Label:** `fase-1` `dev4` `cache` `tdd`

### TASK-11 — Implementar HOF de memoização para classificadores
- **O que fazer:** Função `cached_classify(classifier_fn, cache_size=1024) -> Callable` que envolve qualquer classificador com `lru_cache` baseado no hash do input. Persistir cache em `cache/llm_classifications.json`.
- **Arquivo:** `src/pr_analyzer/cache/memo.py`
- **Entrega:** função + teste verificando que chamada repetida não invoca o classificador original
- **Label:** `fase-1` `dev4` `cache` `tdd`

### TASK-12 — Criar esqueleto tipado do pipeline builder
- **O que fazer:** Definir as assinaturas de `compose()`, `pipe()` e `build_pipeline()` com tipos completos em `pipeline/builder.py`. Implementação pode retornar `NotImplementedError` por enquanto.
- **Arquivo:** `src/pr_analyzer/pipeline/builder.py`
- **Entrega:** arquivo com assinaturas + tipos + docstrings (sem implementação real ainda)
- **Label:** `fase-1` `dev4` `pipeline`

---

## dev5 — Infra e Testes

### TASK-13 — Validar ambiente Docker para todos os devs
- **O que fazer:** Garantir que `docker compose build` e `docker compose up app` funcionam. Documentar qualquer ajuste necessário no `Dockerfile` ou `docker-compose.yml`.
- **Entrega:** Docker funcionando, `http://localhost:8501` abre sem erro
- **Label:** `fase-1` `dev5` `infra`

### TASK-14 — Instalar e validar pre-commit hooks
- **O que fazer:** Executar `make setup` (ou `pip install -e ".[dev]" && pre-commit install`) e confirmar que os hooks rodam em `git commit`. Testar que o hook `no-imperative-loops` bloqueia um `for` em `transforms/`.
- **Entrega:** registro de um commit com hooks passando + um commit bloqueado pelo hook de loop
- **Label:** `fase-1` `dev5` `infra`

### TASK-15 — Criar fixtures compartilhadas em conftest.py
- **O que fazer:** Criar `tests/conftest.py` com fixtures reutilizáveis por todos os devs: `sample_pr`, `sample_pr_no_body`, `sample_prs`, `sample_csv_file` (arquivo temporário), `mock_llm_client`.
- **Arquivo:** `tests/conftest.py`
- **Entrega:** fixtures funcionando + confirmação de que `pytest tests/` roda sem erro (mesmo sem testes de implementação)
- **Label:** `fase-1` `dev5` `tdd` `infra`
