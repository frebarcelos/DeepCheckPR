# Fase 4 — Polimento e Entrega

**Verificação semanal:** 25/05/2026
**Entrega final:** 01/06/2026
**Critério de TOk:** cobertura ≥ 80%, exportação CSV/JSON funcionando na UI, demo end-to-end completa, todos os testes passando no CI.

---

## dev1 — Módulo `io/`

### TASK-40 — Cobertura completa do módulo io/ com edge cases
- **O que fazer:** Atingir 100% de cobertura em `io/csv_reader.py` e `io/exporters.py`. Adicionar testes para: CSV completamente vazio, arquivo com apenas cabeçalho, CSV com encoding Latin-1, linhas com campos extras inesperados.
- **Entrega:** `pytest --cov=src/pr_analyzer/io` mostrando 100%
- **Label:** `fase-4` `dev1` `io` `tdd`

### TASK-41 — Validar integração leitura → pipeline → exportação
- **O que fazer:** Teste de integração end-to-end: ler CSV → filtrar → mapear → exportar para CSV e JSON → verificar conteúdo dos arquivos exportados.
- **Entrega:** teste passando que cobre o fluxo completo de I/O sem LLM
- **Label:** `fase-4` `dev1` `io` `tdd`

---

## dev2 — Módulo `transforms/`

### TASK-42 — Testes com Hypothesis para reducers
- **O que fazer:** Usar a biblioteca `hypothesis` para provar propriedades matemáticas: (1) `count_by_language` de listas concatenadas = soma dos resultados individuais; (2) `aggregate_stats` com 1 elemento = métricas desse elemento; (3) filtros são idempotentes (aplicar 2x = aplicar 1x).
- **Arquivo:** `tests/test_transforms/test_reducers_property.py`
- **Entrega:** pelo menos 3 property-based tests passando
- **Label:** `fase-4` `dev2` `transforms` `tdd`

### TASK-43 — Cobertura completa do módulo transforms/
- **O que fazer:** Atingir 100% de cobertura em `transforms/filters.py`, `mappers.py` e `reducers.py`. Identificar e testar todos os branches não cobertos.
- **Entrega:** `pytest --cov=src/pr_analyzer/transforms` mostrando 100%
- **Label:** `fase-4` `dev2` `transforms` `tdd`

---

## dev3 — Módulo `llm/`

### TASK-44 — Implementar safe_classify() HOF
- **O que fazer:** Função `safe_classify(classifier_fn: Callable, fallback: str) -> Callable` que envolve qualquer classificador com tratamento de saída inválida: se o LLM retornar valor fora do `frozenset` válido, retorna `fallback` sem lançar exceção.
- **Arquivo:** `src/pr_analyzer/llm/classifiers.py`
- **Entrega:** função + testes para resposta válida, resposta inválida e falha de rede (mock lançando exceção)
- **Label:** `fase-4` `dev3` `llm` `tdd`

### TASK-45 — Testes de contrato dos classificadores
- **O que fazer:** Para cada classificador, criar teste que verifica que o output sempre pertence ao conjunto de valores válidos, mesmo com inputs extremos (body com 10.000 caracteres, title vazio, caracteres especiais).
- **Entrega:** testes de contrato passando para os 3 classificadores
- **Label:** `fase-4` `dev3` `llm` `tdd`

---

## dev4 — Módulos `cache/` e `pipeline/`

### TASK-46 — Tornar pipeline configurável por variáveis de ambiente
- **O que fazer:** Função `pipeline_from_env(source: Generator) -> Iterable` que lê variáveis do `.env` para ativar/desativar etapas (ex: `ENABLE_LLM=true`, `FILTER_STATE=merged`, `MIN_CHANGES=10`) e constrói o pipeline correspondente.
- **Arquivo:** `src/pr_analyzer/pipeline/builder.py`
- **Entrega:** função + testes usando `monkeypatch` do pytest para simular variáveis de ambiente
- **Label:** `fase-4` `dev4` `pipeline` `tdd`

### TASK-47 — Cobertura completa dos módulos cache/ e pipeline/
- **O que fazer:** Atingir cobertura ≥ 95% em `cache/memo.py` e `pipeline/builder.py`. Testar casos de cache frio (primeira chamada) e cache quente (hit).
- **Entrega:** `pytest --cov=src/pr_analyzer/cache --cov=src/pr_analyzer/pipeline` mostrando ≥ 95%
- **Label:** `fase-4` `dev4` `cache` `pipeline` `tdd`

---

## dev5 — UI e Entrega Final

### TASK-48 — Implementar exportação CSV e JSON na UI
- **O que fazer:** Botões `st.download_button` para exportar os resultados exibidos (filtrados + classificados) em CSV e JSON. Usar `export_to_csv()` e `export_to_json()` de dev1.
- **Arquivo:** `src/pr_analyzer/ui/app.py`
- **Entrega:** download funcionando na UI com arquivo correto
- **Label:** `fase-4` `dev5` `ui`

### TASK-49 — Garantir cobertura geral ≥ 80%
- **O que fazer:** Rodar `pytest --cov=src/pr_analyzer --cov-report=term-missing` e identificar módulos abaixo de 80%. Coordenar com os outros devs para cobrir os gaps prioritários.
- **Entrega:** relatório de cobertura mostrando ≥ 80% total
- **Label:** `fase-4` `dev5` `tdd` `infra`

### TASK-50 — Merge final para main e validação do CI
- **O que fazer:** Abrir PRs de cada branch `dev/devN` para `main`, revisar com pelo menos 1 colega, garantir que o CI (GitHub Actions) passa em todos os PRs antes do merge. Verificar que a aplicação Streamlit sobe corretamente após o merge.
- **Entrega:** branch `main` com CI verde, aplicação rodando via `make docker-run`
- **Label:** `fase-4` `dev5` `infra`
