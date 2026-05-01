# Fase 3 — Análise Completa + Cache

**Verificação semanal:** 18/05/2026
**Critério de TOk:** os 3 classificadores LLM ativos, cache reduzindo tempo na 2ª execução (demonstrável), UI com pelo menos 2 gráficos de distribuição.

---

## dev1 — Módulo `io/`

### TASK-29 — Detectar schema do CSV automaticamente
- **O que fazer:** Função pura `detect_schema(header: list[str]) -> str` que identifica o formato do CSV (ex: `"kaggle_v1"`, `"kaggle_v2"`) com base nos nomes das colunas. Função HOF `schema_adapter(schema_name: str) -> Callable[[dict], dict]` que retorna a função de mapeamento correta.
- **Arquivo:** `src/pr_analyzer/io/csv_reader.py`
- **Entrega:** funções + testes para os diferentes cabeçalhos do dataset Kaggle
- **Label:** `fase-3` `dev1` `io` `tdd`

### TASK-30 — Tratar linhas malformadas com filter()
- **O que fazer:** Adicionar `filter()` no pipeline de leitura para descartar linhas que falham na validação (campos obrigatórios ausentes, tipos inválidos), sem usar `try/except` como fluxo principal.
- **Arquivo:** `src/pr_analyzer/io/csv_reader.py`
- **Entrega:** função `is_valid_row(row: dict) -> bool` + testes com linhas malformadas e CSV com encoding Latin-1
- **Label:** `fase-3` `dev1` `io` `tdd`

---

## dev2 — Módulo `transforms/`

### TASK-31 — Implementar contagem por tipo de projeto com reduce()
- **O que fazer:** Função `count_by_project_type(enriched_prs: Iterable[EnrichedPR]) -> dict[str, int]` usando `reduce()`. Padrão HOF reutilizando `count_by_field(field: str)`.
- **Arquivo:** `src/pr_analyzer/transforms/reducers.py`
- **Entrega:** função + testes para distribuição com múltiplos tipos e entrada vazia
- **Label:** `fase-3` `dev2` `transforms` `tdd`

### TASK-32 — Implementar contagem por natureza e clareza com reduce()
- **O que fazer:** Funções `count_by_contribution_nature()` e `count_by_description_clarity()` seguindo o mesmo padrão HOF de TASK-31.
- **Arquivo:** `src/pr_analyzer/transforms/reducers.py`
- **Entrega:** funções + testes
- **Label:** `fase-3` `dev2` `transforms` `tdd`

### TASK-33 — Implementar agrupamento de PRs por repositório
- **O que fazer:** Função pura `group_by_repo(prs: Iterable[PRRecord]) -> dict[str, list[PRRecord]]` usando `reduce()` para agrupar PRs do mesmo repositório. Resultado usado por dev3 para batch de chamadas LLM.
- **Arquivo:** `src/pr_analyzer/transforms/reducers.py`
- **Entrega:** função + testes verificando agrupamento correto e imutabilidade (não modifica lista original)
- **Label:** `fase-3` `dev2` `transforms` `tdd`

---

## dev3 — Módulo `llm/`

### TASK-34 — Implementar batch de classificação por repositório
- **O que fazer:** Função `classify_repos_batch(groups: dict[str, list[PRRecord]], client) -> dict[str, str]` que envia 1 chamada LLM por repositório (não por PR) para classificar o tipo de projeto. Usa `map()` sobre os grupos.
- **Arquivo:** `src/pr_analyzer/llm/classifiers.py`
- **Entrega:** função + teste com mock verificando que 1 repositório com 10 PRs gera apenas 1 chamada ao LLM
- **Label:** `fase-3` `dev3` `llm` `tdd`

### TASK-35 — Implementar função de enriquecimento por map()
- **O que fazer:** Função `enrich_prs(prs: Iterable[PRRecord], client) -> Iterable[EnrichedPR]` que aplica os 3 classificadores via `map()` e retorna `EnrichedPR`. Deve usar cache via `cached_classify` de dev4.
- **Arquivo:** `src/pr_analyzer/llm/classifiers.py`
- **Entrega:** função + testes com mock do cliente e do cache
- **Label:** `fase-3` `dev3` `llm` `tdd`

---

## dev4 — Módulos `cache/` e `pipeline/`

### TASK-36 — Integrar cache ao pipeline de enriquecimento
- **O que fazer:** Conectar `cached_classify()` ao pipeline de enriquecimento LLM. Garantir que na 2ª execução com o mesmo dataset os classificadores não são chamados (retornam do cache).
- **Arquivo:** `src/pr_analyzer/cache/memo.py`
- **Entrega:** teste que simula 2 execuções consecutivas e verifica que o mock do LLM é chamado 0 vezes na segunda
- **Label:** `fase-3` `dev4` `cache` `tdd`

### TASK-37 — Implementar pipeline de enriquecimento completo
- **O que fazer:** Função `enrich_pipeline(prs: Iterable[PRRecord], classify_fn: Callable) -> Iterable[EnrichedPR]` e `stats_pipeline(prs: Iterable[PRRecord]) -> Iterable[PRStats]` em `pipeline/builder.py`. Ambas devem ser lazy.
- **Arquivo:** `src/pr_analyzer/pipeline/builder.py`
- **Entrega:** funções + testes verificando laziness e aplicação correta do `classify_fn`
- **Label:** `fase-3` `dev4` `pipeline` `tdd`

---

## dev5 — UI

### TASK-38 — Implementar gráficos de distribuição com Plotly
- **O que fazer:** Exibir na UI 4 gráficos de pizza/barra: distribuição por linguagem, tipo de projeto, natureza da contribuição e clareza da descrição. Usar dados do `count_by_*` de dev2.
- **Arquivo:** `src/pr_analyzer/ui/app.py`
- **Entrega:** gráficos funcionando com dataset real na UI
- **Label:** `fase-3` `dev5` `ui`

### TASK-39 — Implementar toggle de classificação LLM na UI
- **O que fazer:** Quando o toggle "Ativar classificação LLM" estiver ligado, rodar `enrich_prs()` de dev3 e exibir colunas de classificação na tabela. Exibir indicador de "Resultados do cache" quando aplicável.
- **Arquivo:** `src/pr_analyzer/ui/app.py`
- **Entrega:** toggle funcionando, colunas de classificação visíveis, indicador de cache
- **Label:** `fase-3` `dev5` `ui`
