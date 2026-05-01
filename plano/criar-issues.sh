#!/bin/bash
# Cria todas as issues do projeto no GitHub via gh CLI.
# Pré-requisito: gh auth login
# Uso: bash plano/criar-issues.sh
#
# As issues são criadas com labels e milestone.
# O GitHub Projects pode então importar as issues automaticamente.

set -e

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "Criando issues em: $REPO"

create_issue() {
  local title="$1"
  local body="$2"
  local labels="$3"
  local milestone="$4"

  gh issue create \
    --title "$title" \
    --body "$body" \
    --label "$labels" \
    --milestone "$milestone" \
    2>/dev/null && echo "  OK: $title" || echo "  ERRO: $title"
}

# --- Criar labels ---
echo ""
echo "Criando labels..."
for label in fase-1 fase-2 fase-3 fase-4 dev1 dev2 dev3 dev4 dev5 io transforms llm cache pipeline ui tdd infra; do
  gh label create "$label" --force 2>/dev/null || true
done

# --- Criar milestones ---
echo ""
echo "Criando milestones..."
gh api repos/:owner/:repo/milestones --method POST -f title="Fase 1 - Fundação" -f due_on="2026-05-04T23:59:00Z" 2>/dev/null || true
gh api repos/:owner/:repo/milestones --method POST -f title="Fase 2 - Pipeline e LLM" -f due_on="2026-05-11T23:59:00Z" 2>/dev/null || true
gh api repos/:owner/:repo/milestones --method POST -f title="Fase 3 - Análise e Cache" -f due_on="2026-05-18T23:59:00Z" 2>/dev/null || true
gh api repos/:owner/:repo/milestones --method POST -f title="Fase 4 - Polimento e Entrega" -f due_on="2026-05-25T23:59:00Z" 2>/dev/null || true

echo ""
echo "Criando issues — Fase 1..."

create_issue \
  "[dev1] Criar modelo de dados PRRecord" \
  "Definir \`PRRecord\` como \`NamedTuple\` com campos: \`pr_id\`, \`repo_name\`, \`language\`, \`title\`, \`body\`, \`state\`, \`created_at\`, \`merged_at\`, \`additions\`, \`deletions\`, \`changed_files\`.\n\n**Arquivo:** \`src/pr_analyzer/io/csv_reader.py\`\n\n**Entrega:** classe definida + teste verificando imutabilidade." \
  "fase-1,dev1,io,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev1] Implementar leitura lazy do CSV com gerador" \
  "Função \`read_csv_lazy(filepath: str) -> Generator[dict, None, None]\` usando \`csv.DictReader\` e \`yield from\`. Não deve carregar o CSV inteiro em memória.\n\n**Arquivo:** \`src/pr_analyzer/io/csv_reader.py\`\n\n**Entrega:** função + teste que confirma retorno de \`GeneratorType\`." \
  "fase-1,dev1,io,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev1] Implementar normalização de schema (apply_schema)" \
  "Função pura \`apply_schema(raw_row: dict) -> PRRecord\` que converte dict bruto em \`PRRecord\`, normalizando tipos com fallback para campos ausentes.\n\n**Arquivo:** \`src/pr_analyzer/io/csv_reader.py\`\n\n**Entrega:** função + testes para campo ausente, tipo inválido, language em maiúsculo." \
  "fase-1,dev1,io,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev1] Implementar pipeline completo read_prs()" \
  "Função \`read_prs(filepath: str) -> Generator[PRRecord, None, None]\` compondo \`read_csv_lazy\` + \`apply_schema\` em expressão geradora.\n\n**Arquivo:** \`src/pr_analyzer/io/csv_reader.py\`" \
  "fase-1,dev1,io,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev2] Implementar filtros por estado e linguagem" \
  "Funções \`by_state(state)\` e \`by_language(language)\` retornando predicados \`Callable[[PRRecord], bool]\`. Case-insensitive, sem efeitos colaterais.\n\n**Arquivo:** \`src/pr_analyzer/transforms/filters.py\`" \
  "fase-1,dev2,transforms,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev2] Implementar filtro por intervalo de datas" \
  "Função \`by_date_range(start, end) -> Callable[[PRRecord], bool]\` comparando \`created_at[:10]\` com strings ISO 8601.\n\n**Arquivo:** \`src/pr_analyzer/transforms/filters.py\`" \
  "fase-1,dev2,transforms,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev2] Implementar filtros auxiliares e combinador" \
  "Funções \`with_non_empty_body()\`, \`with_min_size(min_changes)\` e HOF \`combine_filters(*predicates)\` com \`all()\`. Lista vazia deve retornar True.\n\n**Arquivo:** \`src/pr_analyzer/transforms/filters.py\`" \
  "fase-1,dev2,transforms,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev3] Configurar cliente Agno + Groq" \
  "Função \`create_groq_client()\` que lê \`GROQ_API_KEY\` e \`LLM_MODEL\` do \`.env\` e retorna agente Agno.\n\n**Arquivo:** \`src/pr_analyzer/llm/client.py\`" \
  "fase-1,dev3,llm,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev3] Definir interface dos classificadores com stubs" \
  "Criar 3 funções com assinaturas completas e stubs: \`classify_project_type\`, \`classify_contribution_nature\`, \`classify_description_clarity\`. Incluir \`frozenset\` com valores válidos.\n\n**Arquivo:** \`src/pr_analyzer/llm/classifiers.py\`" \
  "fase-1,dev3,llm,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev4] Implementar geração de chave de cache com hashlib" \
  "Função pura \`make_cache_key(*args: str) -> str\` gerando hash SHA-256 determinístico.\n\n**Arquivo:** \`src/pr_analyzer/cache/memo.py\`\n\n**Testes:** determinismo e unicidade." \
  "fase-1,dev4,cache,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev4] Implementar HOF de memoização cached_classify()" \
  "Função \`cached_classify(classifier_fn, cache_size=1024)\` com \`lru_cache\` por hash. Persistir em \`cache/llm_classifications.json\`.\n\n**Arquivo:** \`src/pr_analyzer/cache/memo.py\`" \
  "fase-1,dev4,cache,tdd" "Fase 1 - Fundação"

create_issue \
  "[dev4] Criar esqueleto tipado do pipeline builder" \
  "Definir assinaturas de \`compose()\`, \`pipe()\` e \`build_pipeline()\` com tipos completos. Implementação pode ser \`NotImplementedError\`.\n\n**Arquivo:** \`src/pr_analyzer/pipeline/builder.py\`" \
  "fase-1,dev4,pipeline" "Fase 1 - Fundação"

create_issue \
  "[dev5] Validar ambiente Docker para todos os devs" \
  "\`docker compose build\` e \`docker compose up app\` devem funcionar. \`localhost:8501\` deve abrir sem erro." \
  "fase-1,dev5,infra" "Fase 1 - Fundação"

create_issue \
  "[dev5] Instalar e validar pre-commit hooks" \
  "Executar \`make setup\` e confirmar hooks no \`git commit\`. Testar que \`no-imperative-loops\` bloqueia \`for\` em \`transforms/\`." \
  "fase-1,dev5,infra" "Fase 1 - Fundação"

create_issue \
  "[dev5] Criar fixtures compartilhadas em conftest.py" \
  "Fixtures: \`sample_pr\`, \`sample_pr_no_body\`, \`sample_prs\`, \`sample_csv_file\` (tmp_path), \`mock_llm_client\`.\n\n**Arquivo:** \`tests/conftest.py\`" \
  "fase-1,dev5,tdd,infra" "Fase 1 - Fundação"

echo ""
echo "Criando issues — Fase 2..."

create_issue "[dev1] Implementar serialização pura de records" "Função pura \`serialize_records(records) -> list[dict]\` usando \`map()\` + \`_asdict()\`.\n\n**Arquivo:** \`src/pr_analyzer/io/exporters.py\`" "fase-2,dev1,io,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev1] Implementar exportação para CSV e JSON" "Funções \`export_to_csv()\` e \`export_to_json()\` usando \`serialize_records()\`. Testes com \`tmp_path\`.\n\n**Arquivo:** \`src/pr_analyzer/io/exporters.py\`" "fase-2,dev1,io,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev1] Integrar leitura com pipeline" "Teste de integração: \`read_prs(csv) → build_pipeline → list()\` produz PRRecords corretos sem materializar." "fase-2,dev1,io,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev2] Implementar compute_stats() com map()" "Função pura \`compute_stats(pr) -> PRStats\` com body_char_count, body_word_count, total_changes, is_merged.\n\n**Arquivo:** \`src/pr_analyzer/transforms/mappers.py\`" "fase-2,dev2,transforms,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev2] Implementar count_by_language() com reduce()" "Usando \`functools.reduce()\`. Acumulador com dict union (\`|\`), nunca \`update()\`.\n\n**Arquivo:** \`src/pr_analyzer/transforms/reducers.py\`" "fase-2,dev2,transforms,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev2] Implementar aggregate_stats() com reduce()" "Função \`aggregate_stats(stats) -> dict\` com avg_chars, avg_words, avg_changes, merge_rate usando \`reduce()\`.\n\n**Arquivo:** \`src/pr_analyzer/transforms/reducers.py\`" "fase-2,dev2,transforms,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev3] Implementar classify_project_type() com LLM real" "Substituir stub. Prompt retorna JSON \`{\"project_type\": \"...\"}\`. Validar contra frozenset. Teste \`@pytest.mark.integration\`.\n\n**Arquivo:** \`src/pr_analyzer/llm/classifiers.py\`" "fase-2,dev3,llm,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev3] Implementar classify_contribution_nature() com LLM real" "Substituir stub. Prompt usa title + 300 chars do body, retorna JSON.\n\n**Arquivo:** \`src/pr_analyzer/llm/classifiers.py\`" "fase-2,dev3,llm,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev3] Implementar classify_description_clarity() com LLM real" "Substituir stub. Body vazio retorna \`insufficient\` sem chamar LLM. Prompt usa 500 chars.\n\n**Arquivo:** \`src/pr_analyzer/llm/classifiers.py\`" "fase-2,dev3,llm,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev4] Implementar compose() e pipe()" "Funções puras usando \`reduce()\`. Testes para 1, 2 e 3 funções encadeadas.\n\n**Arquivo:** \`src/pr_analyzer/pipeline/builder.py\`" "fase-2,dev4,pipeline,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev4] Implementar build_pipeline() lazy completo" "Usando \`filter()\` e \`map()\` nativos. Resultado deve ser lazy (não list).\n\n**Arquivo:** \`src/pr_analyzer/pipeline/builder.py\`" "fase-2,dev4,pipeline,tdd" "Fase 2 - Pipeline e LLM"
create_issue "[dev5] Implementar upload e leitura do CSV na UI" "\`st.file_uploader\` + \`read_prs()\` + \`st.dataframe\` com primeiras 20 linhas.\n\n**Arquivo:** \`src/pr_analyzer/ui/app.py\`" "fase-2,dev5,ui" "Fase 2 - Pipeline e LLM"
create_issue "[dev5] Implementar filtros básicos na sidebar da UI" "Conectar \`by_state\`, \`by_language\`, \`by_date_range\` ao \`build_pipeline()\`. Tabela atualiza ao mudar filtros.\n\n**Arquivo:** \`src/pr_analyzer/ui/app.py\`" "fase-2,dev5,ui" "Fase 2 - Pipeline e LLM"

echo ""
echo "Criando issues — Fase 3..."

create_issue "[dev1] Detectar schema do CSV automaticamente" "Função pura \`detect_schema(header)\` e HOF \`schema_adapter(schema_name)\`.\n\n**Arquivo:** \`src/pr_analyzer/io/csv_reader.py\`" "fase-3,dev1,io,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev1] Tratar linhas malformadas com filter()" "Função \`is_valid_row(row) -> bool\` + \`filter()\` no pipeline. Sem try/except como fluxo principal.\n\n**Arquivo:** \`src/pr_analyzer/io/csv_reader.py\`" "fase-3,dev1,io,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev2] Implementar count_by_project_type() com reduce()" "HOF \`count_by_field(field)\` reutilizável. \`count_by_project_type\` como instância.\n\n**Arquivo:** \`src/pr_analyzer/transforms/reducers.py\`" "fase-3,dev2,transforms,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev2] Implementar count_by_contribution_nature() e count_by_description_clarity()" "Seguir padrão HOF de \`count_by_field()\`.\n\n**Arquivo:** \`src/pr_analyzer/transforms/reducers.py\`" "fase-3,dev2,transforms,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev2] Implementar group_by_repo() com reduce()" "Função pura \`group_by_repo(prs) -> dict\` usando \`reduce()\` para agrupar por repositório.\n\n**Arquivo:** \`src/pr_analyzer/transforms/reducers.py\`" "fase-3,dev2,transforms,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev3] Implementar batch de classificação por repositório" "Função \`classify_repos_batch(groups, client)\` com 1 chamada LLM por repo. Teste: 1 repo com 10 PRs gera 1 chamada.\n\n**Arquivo:** \`src/pr_analyzer/llm/classifiers.py\`" "fase-3,dev3,llm,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev3] Implementar enrich_prs() com map()" "Função \`enrich_prs(prs, client) -> Iterable[EnrichedPR]\` usando \`map()\` com 3 classificadores + cache.\n\n**Arquivo:** \`src/pr_analyzer/llm/classifiers.py\`" "fase-3,dev3,llm,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev4] Integrar cache ao pipeline de enriquecimento" "Conectar \`cached_classify()\` ao pipeline. Teste: 2ª execução não chama o mock LLM.\n\n**Arquivo:** \`src/pr_analyzer/cache/memo.py\`" "fase-3,dev4,cache,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev4] Implementar enrich_pipeline() e stats_pipeline()" "Funções lazy. \`enrich_pipeline(prs, classify_fn) -> Iterable[EnrichedPR]\` e \`stats_pipeline(prs) -> Iterable[PRStats]\`.\n\n**Arquivo:** \`src/pr_analyzer/pipeline/builder.py\`" "fase-3,dev4,pipeline,tdd" "Fase 3 - Análise e Cache"
create_issue "[dev5] Implementar gráficos de distribuição com Plotly" "4 gráficos: linguagem, tipo de projeto, natureza, clareza. Usar \`count_by_*\` de dev2.\n\n**Arquivo:** \`src/pr_analyzer/ui/app.py\`" "fase-3,dev5,ui" "Fase 3 - Análise e Cache"
create_issue "[dev5] Implementar toggle de classificação LLM na UI" "Toggle Liga/Desliga enrich_prs(). Colunas de classificação aparecem na tabela. Indicador de cache hit.\n\n**Arquivo:** \`src/pr_analyzer/ui/app.py\`" "fase-3,dev5,ui" "Fase 3 - Análise e Cache"

echo ""
echo "Criando issues — Fase 4..."

create_issue "[dev1] Cobertura completa do módulo io/ com edge cases" "100% em csv_reader.py e exporters.py. Testes: CSV vazio, só cabeçalho, Latin-1, campos extras." "fase-4,dev1,io,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev1] Teste de integração leitura → pipeline → exportação" "End-to-end: ler CSV → filtrar → mapear → exportar CSV e JSON → verificar conteúdo." "fase-4,dev1,io,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev2] Testes com Hypothesis para reducers" "Property-based tests: count concatenado = soma; aggregate com 1 elemento; filtros idempotentes.\n\n**Arquivo:** \`tests/test_transforms/test_reducers_property.py\`" "fase-4,dev2,transforms,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev2] Cobertura completa do módulo transforms/" "100% em filters.py, mappers.py e reducers.py." "fase-4,dev2,transforms,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev3] Implementar safe_classify() HOF" "HOF \`safe_classify(classifier_fn, fallback)\` para output inválido do LLM. Testes: resposta válida, inválida, exceção de rede.\n\n**Arquivo:** \`src/pr_analyzer/llm/classifiers.py\`" "fase-4,dev3,llm,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev3] Testes de contrato dos classificadores" "Output sempre pertence ao frozenset válido com inputs extremos (10k chars, title vazio, caracteres especiais)." "fase-4,dev3,llm,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev4] Tornar pipeline configurável por variáveis de ambiente" "Função \`pipeline_from_env(source)\` lendo \`ENABLE_LLM\`, \`FILTER_STATE\`, \`MIN_CHANGES\`. Testes com \`monkeypatch\`.\n\n**Arquivo:** \`src/pr_analyzer/pipeline/builder.py\`" "fase-4,dev4,pipeline,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev4] Cobertura ≥ 95% em cache/ e pipeline/" "pytest --cov mostrando ≥ 95%. Testar cache frio e cache quente." "fase-4,dev4,cache,pipeline,tdd" "Fase 4 - Polimento e Entrega"
create_issue "[dev5] Implementar exportação CSV e JSON na UI" "\`st.download_button\` para exportar resultados filtrados + classificados.\n\n**Arquivo:** \`src/pr_analyzer/ui/app.py\`" "fase-4,dev5,ui" "Fase 4 - Polimento e Entrega"
create_issue "[dev5] Garantir cobertura geral ≥ 80%" "pytest --cov=src/pr_analyzer --cov-report=term-missing. Coordenar gaps com outros devs." "fase-4,dev5,tdd,infra" "Fase 4 - Polimento e Entrega"
create_issue "[dev5] Merge final para main e validação do CI" "PRs de dev/devN para main com revisão. CI verde antes de merge. \`make docker-run\` funciona." "fase-4,dev5,infra" "Fase 4 - Polimento e Entrega"

echo ""
echo "Todas as issues criadas. Acesse o GitHub Projects para organizar no Kanban."
echo "Repo: https://github.com/$REPO"
