# Fase 2 — Pipeline + LLM Real

**Verificação semanal:** 11/05/2026
**Critério de TOk:** pipeline lazy filtrando PRs do CSV, pelo menos 1 classificador LLM retornando resultado real (não stub), UI exibindo tabela de PRs.

---

## dev1 — Módulo `io/`

### TASK-16 — Implementar serialização pura de records
- **O que fazer:** Função pura `serialize_records(records: Iterable) -> list[dict]` que converte `NamedTuple` ou dict em lista de dicts serializáveis, usando `map()` + `_asdict()`. Separar serialização (pura) de escrita em disco (efeito colateral).
- **Arquivo:** `src/pr_analyzer/io/exporters.py`
- **Entrega:** função + testes verificando que `NamedTuple` e dict são convertidos corretamente
- **Label:** `fase-2` `dev1` `io` `tdd`

### TASK-17 — Implementar exportação para CSV e JSON
- **O que fazer:** Funções `export_to_csv(records, filepath)` e `export_to_json(records, filepath)` que consomem um iterável e escrevem em disco. Devem chamar `serialize_records()` internamente.
- **Arquivo:** `src/pr_analyzer/io/exporters.py`
- **Entrega:** funções + testes usando `tmp_path` do pytest para verificar conteúdo do arquivo gerado
- **Label:** `fase-2` `dev1` `io` `tdd`

### TASK-18 — Integrar leitura com pipeline
- **O que fazer:** Confirmar que `read_prs()` pode ser passado diretamente para `build_pipeline()` do dev4 sem materializar a coleção. Ajustar tipagem se necessário.
- **Entrega:** teste de integração end-to-end: `read_prs(csv) → build_pipeline → list()` produz `PRRecord`s corretos
- **Label:** `fase-2` `dev1` `io` `tdd`

---

## dev2 — Módulo `transforms/`

### TASK-19 — Implementar métricas por PR com map()
- **O que fazer:** Função pura `compute_stats(pr: PRRecord) -> PRStats` que retorna `PRStats` (NamedTuple) com `body_char_count`, `body_word_count`, `total_changes`, `is_merged`. Deve ser usada via `map()` no pipeline.
- **Arquivo:** `src/pr_analyzer/transforms/mappers.py`
- **Entrega:** função + testes para PR com body vazio, PR sem merge, contagem de palavras
- **Label:** `fase-2` `dev2` `transforms` `tdd`

### TASK-20 — Implementar contagem por linguagem com reduce()
- **O que fazer:** Função pura `count_by_language(prs: Iterable[PRRecord]) -> dict[str, int]` usando `functools.reduce()`. Acumulador deve ser construído com `|` (dict union), nunca com `.update()` ou `[]= `.
- **Arquivo:** `src/pr_analyzer/transforms/reducers.py`
- **Entrega:** função + testes incluindo entrada vazia e linguagem `unknown`
- **Label:** `fase-2` `dev2` `transforms` `tdd`

### TASK-21 — Implementar agregação estatística com reduce()
- **O que fazer:** Função pura `aggregate_stats(stats: Iterable[PRStats]) -> dict[str, float]` usando `reduce()` para acumular soma e calcular médias de `avg_chars`, `avg_words`, `avg_changes`, `merge_rate`.
- **Arquivo:** `src/pr_analyzer/transforms/reducers.py`
- **Entrega:** função + testes para 0 PRs, 1 PR e múltiplos PRs
- **Label:** `fase-2` `dev2` `transforms` `tdd`

---

## dev3 — Módulo `llm/`

### TASK-22 — Implementar classificador de tipo de projeto
- **O que fazer:** Substituir stub de `classify_project_type()` por implementação real. Prompt deve receber `repo_name` + sample de títulos de PRs e retornar JSON `{"project_type": "..."}`. Parsear resposta e validar contra `frozenset` de valores válidos.
- **Arquivo:** `src/pr_analyzer/llm/classifiers.py`
- **Entrega:** função + teste de integração marcado `@pytest.mark.integration` + teste unitário com mock
- **Label:** `fase-2` `dev3` `llm` `tdd`

### TASK-23 — Implementar classificador de natureza da contribuição
- **O que fazer:** Substituir stub de `classify_contribution_nature()` por implementação real. Prompt usa `title` + primeiros 300 chars do `body` e retorna JSON `{"contribution_nature": "..."}`.
- **Arquivo:** `src/pr_analyzer/llm/classifiers.py`
- **Entrega:** função + teste de integração + teste unitário com mock
- **Label:** `fase-2` `dev3` `llm` `tdd`

### TASK-24 — Implementar classificador de clareza da descrição
- **O que fazer:** Substituir stub de `classify_description_clarity()` por implementação real. Body vazio deve retornar `"insufficient"` direto, sem chamar LLM. Prompt usa primeiros 500 chars.
- **Arquivo:** `src/pr_analyzer/llm/classifiers.py`
- **Entrega:** função + teste de integração + teste unitário com mock + teste para body vazio (não deve chamar LLM)
- **Label:** `fase-2` `dev3` `llm` `tdd`

---

## dev4 — Módulos `cache/` e `pipeline/`

### TASK-25 — Implementar compose() e pipe()
- **O que fazer:** Função pura `compose(*fns) -> Callable` que compõe N funções da esquerda para direita usando `reduce()`. Função pura `pipe(value, *fns)` que aplica funções sequencialmente a um valor.
- **Arquivo:** `src/pr_analyzer/pipeline/builder.py`
- **Entrega:** funções + testes para 1 função, 2 funções e 3 funções encadeadas
- **Label:** `fase-2` `dev4` `pipeline` `tdd`

### TASK-26 — Implementar build_pipeline() lazy completo
- **O que fazer:** Função `build_pipeline(source, filters=None, mappers=None) -> Iterable[PRRecord]` que aplica filtros com `filter()` nativo e mappers com `map()` nativo. Pipeline deve permanecer lazy (não converter para lista internamente).
- **Arquivo:** `src/pr_analyzer/pipeline/builder.py`
- **Entrega:** função + testes: sem filtros retorna todos, com filtro retorna subconjunto, resultado é lazy (não é `list`)
- **Label:** `fase-2` `dev4` `pipeline` `tdd`

---

## dev5 — UI

### TASK-27 — Implementar upload e leitura do CSV na UI
- **O que fazer:** No Streamlit, receber arquivo via `st.file_uploader`, salvar em arquivo temporário e passar para `read_prs()`. Exibir número de PRs lidos e as primeiras 20 linhas em `st.dataframe`.
- **Arquivo:** `src/pr_analyzer/ui/app.py`
- **Entrega:** funcionalidade testada manualmente com dataset real; screenshot ou descrição do resultado
- **Label:** `fase-2` `dev5` `ui`

### TASK-28 — Implementar filtros básicos na sidebar da UI
- **O que fazer:** Conectar os filtros da sidebar (`by_state`, `by_language`, `by_date_range`) ao `build_pipeline()`. Reexibir tabela filtrada quando o usuário mudar os selects.
- **Arquivo:** `src/pr_analyzer/ui/app.py`
- **Entrega:** filtragem funcionando na UI com os filtros do módulo `transforms/`
- **Label:** `fase-2` `dev5` `ui`
