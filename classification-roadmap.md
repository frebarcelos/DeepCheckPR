# Roadmap de Melhorias — Pipeline de Classificação LLM

Escopo: módulos `llm/`, `cache/`, `pipeline/` e integrações com UI.
Referência de estado atual: Sprint 4 concluída (2026-05-25).

---

## Estado atual (implementado)

| Recurso | Arquivo | Ganho |
|---|---|---|
| Skills: system prompt + few-shot | `llm/skills.py` | Modelos pequenos seguem JSON |
| Tool calling (1 chamada/PR) | `llm/classifiers.py` | 3× menos chamadas que modo texto |
| ThreadPoolExecutor (`max_workers`) | `llm/classifiers.py` | N× paralelo |
| Batch N PRs por chamada | `llm/classifiers.py` | 5–10× menos round-trips |
| `OLLAMA_NUM_PARALLEL` no systemd | host config | Ollama processa N simultâneos |
| Cache em memória + disco | `cache/memo.py` | 2ª execução ≈ 0s |
| Auto-detecção de hardware | `llm/system_probe.py` | Escala workers/batch ao hardware |
| **Retry com backoff (LLM-07)** ✅ | `llm/client.py` | Resiliência a timeouts transientes |
| **Adaptive batch size (LLM-02)** ✅ | `llm/classifiers.py` | Elimina fallbacks caros automaticamente |
| **Heurísticas de pré-classificação (LLM-04)** ✅ | `transforms/heuristics.py` | 10–30% das chamadas eliminadas |

---

## TASK-LLM-01 — Async HTTP client (asyncio + aiohttp) ✅ CONCLUÍDA (2026-05-26)

**Prioridade:** Alta
**Esforço:** Médio (3–5 dias)
**Ganho esperado:** 2–4× no throughput vs ThreadPoolExecutor
**Dev sugerido:** dev3 (Dean)

### Problema atual
`ThreadPoolExecutor` usa threads do sistema operacional. Cada thread bloqueia no I/O de rede esperando a resposta do Ollama. Com 8+ workers isso satura o scheduler do SO antes de saturar a rede.

### O que implementar
- Criar `AsyncLLMClient` Protocol com `async def run(...)` em `llm/client.py`
- Implementar `_AsyncOllamaClient` usando `aiohttp.ClientSession` com connection pool
- Adicionar `async def enrich_prs_async(...)` em `llm/classifiers.py`
- `asyncio.gather(*tasks)` substitui o `ThreadPoolExecutor`

### Interface alvo
```python
# llm/client.py
class AsyncLLMClient(Protocol):
    async def run(self, message: str, **kwargs: Any) -> Any: ...

# llm/classifiers.py
async def enrich_prs_async(
    prs: Iterable[PRRecord],
    client: AsyncLLMClient,
    batch_size: int = 5,
    concurrency: int = 8,
) -> list[EnrichedPR]: ...
```

### Testes (TDD)
- `test_async_ollama_client_envia_request_correto`
- `test_enrich_prs_async_retorna_lista_enriched_pr`
- `test_enrich_prs_async_respeita_concurrency_limit`

### Observação
Manter `enrich_prs()` síncrono como fallback — a UI Streamlit não é async-native.

---

## TASK-LLM-02 — Adaptive batch size com backoff ✅ CONCLUÍDA (2026-05-25)

**Prioridade:** Alta
**Esforço:** Baixo (1 dia)
**Ganho esperado:** Elimina perda de tempo com fallbacks frequentes
**Dev sugerido:** dev3 (Dean)

### Problema atual
`batch_size=10` com qwen2:1.5b falha ~35% das vezes → cai em 10 chamadas individuais → custo real maior que `batch_size=5`. O usuário precisa calibrar manualmente.

### O que implementar
- Em `_enrich_prs_batch_call()`: contar falhas consecutivas
- Após 3 falhas: reduzir `batch_size` pela metade automaticamente
- Após 10 sucessos: tentar aumentar de volta (até o máximo configurado)
- Expor `AdaptiveBatchState` como dataclass imutável para testes

### Interface alvo
```python
# llm/classifiers.py
from dataclasses import dataclass

@dataclass(frozen=True)
class BatchState:
    current_size: int
    consecutive_failures: int
    consecutive_successes: int

def adapt_batch_size(state: BatchState, success: bool, max_size: int) -> BatchState: ...
```

### Testes (TDD)
- `test_adapt_batch_size_reduz_apos_3_falhas`
- `test_adapt_batch_size_aumenta_apos_10_sucessos`
- `test_adapt_batch_size_nao_ultrapassa_max_size`

---

## TASK-LLM-03 — HTTP keep-alive e connection pooling ✅ CONCLUÍDA (2026-05-26)

**Prioridade:** Média
**Esforço:** Baixo (meio dia)
**Ganho esperado:** 5–15% de redução de latência
**Dev sugerido:** dev3 (Dean)

### Problema atual
`_OllamaDirectClient.run()` cria uma nova conexão TCP para cada chamada via `urllib.request.urlopen`. Com 2000 PRs em batch=5 = 400 chamadas → 400 handshakes TCP.

### O que implementar
- Substituir `urllib.request` por `http.client.HTTPConnection` com reuso de socket
- Ou usar `urllib3` (já incluída pelo requests/streamlit) com pool

```python
# llm/client.py
import http.client, json

class _OllamaDirectClient:
    def __init__(self, model, host, system_prompt=""):
        ...
        parsed = urllib.parse.urlparse(host)
        self._conn = http.client.HTTPConnection(parsed.netloc)  # reutilizado
```

### Testes (TDD)
- `test_ollama_client_reusa_conexao_entre_chamadas`
- `test_ollama_client_reconecta_se_conexao_fechada`

---

## TASK-LLM-04 — Heurística pré-classificação (skip LLM para casos óbvios) ✅ CONCLUÍDA (2026-05-25)

**Prioridade:** Média
**Esforço:** Baixo (1 dia)
**Ganho esperado:** 10–30% de chamadas eliminadas (dependendo do dataset)
**Dev sugerido:** dev3 (Dean) + dev2 (Pedro — função pura em `transforms/`)

### Problema atual
Casos triviais vão para o LLM desnecessariamente:
- Título `"fix typo in README"` → claramente `natureza=documentação, clareza=básica`
- Body vazio → `clareza=insuficiente` (já implementado só para clareza; falta tipo e natureza)
- Título vazio + body vazio → todos os campos são `"outro"/"insuficiente"`

### O que implementar
Função pura em `transforms/` (sem I/O) que retorna classificação heurística ou `None`:

```python
# transforms/heuristics.py  (módulo PURO — zero I/O)
_BUG_KEYWORDS:   frozenset[str] = frozenset({"fix", "bug", "crash", "error", "patch"})
_FEAT_KEYWORDS:  frozenset[str] = frozenset({"add", "implement", "feature", "support"})
_DOC_KEYWORDS:   frozenset[str] = frozenset({"doc", "readme", "changelog", "comment"})
_REFAC_KEYWORDS: frozenset[str] = frozenset({"refactor", "clean", "rename", "move"})

def heuristic_nature(title: str) -> str | None:
    """Retorna natureza se óbvio pelo título, None caso contrário."""
    ...

def heuristic_classify(pr: PRRecord) -> EnrichedPR | None:
    """Retorna EnrichedPR sem chamar LLM, ou None se incerto."""
    ...
```

Em `llm/classifiers.py`: verificar heurística antes de chamar LLM.

### Testes (TDD)
- `test_heuristic_nature_fix_retorna_bug_fix`
- `test_heuristic_nature_incerto_retorna_none`
- `test_heuristic_classify_body_vazio_titulo_vazio_retorna_defaults`
- Property-based: `heuristic_classify` nunca retorna valores fora dos frozensets

---

## TASK-LLM-05 — Cache de tipo por repositório no modo tools ✅ CONCLUÍDA (2026-05-26)

**Prioridade:** Média
**Esforço:** Baixo (1 dia)
**Ganho esperado:** Reduz ~33% das chamadas se dataset tem PRs repetidos por repo
**Dev sugerido:** dev4 (Frederico)

### Problema atual
No modo `use_tools=True`, cada PR chama o LLM para os 3 campos incluindo `tipo_projeto`. Mas `tipo_projeto` é uma propriedade do **repositório**, não do PR individual — todos os PRs de `django/django` têm o mesmo tipo.

`classify_repos_batch()` já faz isso no modo não-tools, mas não está integrado ao caminho tools/batch.

### O que implementar
- Em `enrich_prs()` com `use_tools=True`: pré-classificar repos com `classify_repos_batch()`
- Resultado: `dict[str, str]` repo → tipo
- No `enrich_pr_with_tools()`: aceitar `repo_type_cache: dict[str, str] | None` opcional
- Se cache tem o repo: omitir `tipo_projeto` da ferramenta (reduz output tokens)

```python
# llm/classifiers.py
def enrich_pr_with_tools(
    pr: PRRecord,
    client: LLMClient,
    repo_type_cache: dict[str, str] | None = None,
) -> EnrichedPR: ...
```

### Testes (TDD)
- `test_enrich_pr_with_tools_usa_cache_de_repo`
- `test_enrich_pr_with_tools_sem_cache_classifica_tipo`
- `test_enrich_prs_pre_classifica_repos_antes_dos_prs`

---

## TASK-LLM-06 — Métricas de qualidade e observabilidade ✅ CONCLUÍDA (2026-05-26)

**Prioridade:** Média
**Esforço:** Médio (2–3 dias)
**Ganho esperado:** Diagnóstico de falhas, benchmarking de modelos
**Dev sugerido:** dev3 (Dean) + dev5 (Diogo — UI)

### Problema atual
Não há visibilidade sobre:
- Taxa de fallback por batch (modelo falhando silenciosamente)
- Tempo médio por chamada por tipo de classificação
- Distribuição de valores retornados (concentração em "outro" indica problema)

### O que implementar

**`llm/metrics.py`** (novo módulo, efeito colateral permitido):
```python
from dataclasses import dataclass, field

@dataclass
class ClassificationMetrics:
    total_prs: int = 0
    batch_calls: int = 0
    batch_fallbacks: int = 0
    individual_calls: int = 0
    total_time_s: float = 0.0
    value_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def fallback_rate(self) -> float:
        return self.batch_fallbacks / self.batch_calls if self.batch_calls else 0.0

    @property
    def throughput_prs_per_min(self) -> float:
        return (self.total_prs / self.total_time_s * 60) if self.total_time_s else 0.0
```

**Na UI** (`ui/app.py`): exibir métricas em `st.expander("Métricas de classificação")` após o enriquecimento.

### Testes (TDD)
- `test_metrics_fallback_rate_calculado_corretamente`
- `test_metrics_throughput_calculado_corretamente`
- `test_metrics_value_counts_acumulam`

---

## TASK-LLM-07 — Retry com exponential backoff ✅ CONCLUÍDA (2026-05-25)

**Prioridade:** Média
**Esforço:** Baixo (meio dia)
**Ganho esperado:** Elimina falhas por timeout transiente do Ollama
**Dev sugerido:** dev3 (Dean)

### Problema atual
`_OllamaDirectClient.run()` faz exatamente 1 tentativa. Se o Ollama estiver sobrecarregado (comum com `OLLAMA_NUM_PARALLEL=4` e `max_workers=8`) a chamada pode expirar (timeout=120s) e o PR recebe classificação de fallback.

### O que implementar
```python
# llm/client.py
def _with_retry(
    fn: Callable[[], Any],
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """Tenta fn até max_attempts vezes com backoff exponencial."""
    ...
```

Configurável via env: `LLM_MAX_RETRIES=3`, `LLM_RETRY_BASE_DELAY=1.0`.

### Testes (TDD)
- `test_with_retry_sucesso_na_primeira`
- `test_with_retry_sucesso_na_terceira`
- `test_with_retry_levanta_apos_max_attempts`
- `test_with_retry_respeita_base_delay` (mock de sleep)

---

## TASK-LLM-08 — Benchmark automático de modelos

**Prioridade:** Baixa
**Esforço:** Médio (2–3 dias)
**Ganho esperado:** Escolha informada do modelo para cada ambiente
**Dev sugerido:** dev3 (Dean)

### O que implementar
Script `scripts/benchmark_llm.py` que:
1. Carrega N PRs do dataset (`DATASET_PATH`)
2. Testa cada modelo disponível no Ollama com `ollama list`
3. Para cada modelo: mede tempo médio/call, taxa de JSON válido, taxa de valores no frozenset
4. Gera tabela markdown com resultado

```bash
python scripts/benchmark_llm.py --prs 50 --batch-sizes 1,5,10
```

Saída esperada:
```
| Modelo        | calls/min | JSON ok% | valores válidos% | batch=5 fail% |
|---------------|-----------|----------|------------------|---------------|
| tinyllama:1.1b|        12 |      45% |              60% |           80% |
| qwen2:1.5b    |        18 |      95% |              98% |            5% |
| phi3:mini     |        14 |      97% |              99% |            3% |
```

---

## TASK-LLM-09 — Prompt compression ✅ CONCLUÍDA (2026-05-26)

**Prioridade:** Baixa
**Esforço:** Baixo (meio dia)
**Ganho esperado:** 10–20% de redução no tempo de prompt eval
**Dev sugerido:** dev3 (Dean)

### Problema atual
No modo batch, o prompt inclui até 200 chars de body por PR. Com batch=10 isso gera prompts de ~2000 tokens. Tokens de prompt são processados sequencialmente — menos tokens = menos tempo.

### O que implementar
- Truncar body para 100 chars em modo batch (200 em chamada individual)
- Comprimir o prompt do PR para formato compacto:

```
# Atual (verbose):
PR 0: repo=facebook/react | title=fix useState hook | body=This PR fixes...

# Comprimido:
0|facebook/react|fix useState hook|This PR fixes the...
```

- Configurável via env `LLM_BODY_CHARS_BATCH=100`, `LLM_BODY_CHARS_SINGLE=400`

### Testes (TDD)
- `test_batch_prompt_trunca_body_para_100_chars`
- `test_single_prompt_trunca_body_para_400_chars`

---

## TASK-LLM-10 — Persistent cache com SQLite ✅ CONCLUÍDA (2026-05-26)

**Prioridade:** Baixa
**Esforço:** Médio (2 dias)
**Ganho esperado:** Cache persiste entre containers Docker e entre versões do dataset
**Dev sugerido:** dev4 (Frederico)

### Problema atual
O cache atual (`cache/memo.py`) persiste em JSON por arquivo. Problemas:
- JSON inteiro é reescrito a cada nova entrada (lento para caches grandes)
- Não suporta acesso concorrente (race condition com `max_workers > 1`)
- Perdido ao reconstruir o container Docker

### O que implementar
- Novo backend `cache/sqlite_store.py` usando `sqlite3` da stdlib
- `make_enriched_classifier()` aceita `cache_backend: Literal["json", "sqlite"] = "json"`
- SQLite tem `WAL mode` para leituras concorrentes sem lock
- Volume Docker para persistência além do container

```python
# cache/sqlite_store.py
def make_sqlite_cache(
    db_path: Path,
    table: str = "classifications",
) -> Callable[[str], str | None]: ...
```

### Testes (TDD)
- `test_sqlite_cache_persiste_entre_instancias`
- `test_sqlite_cache_acesso_concorrente_sem_corrida`
- `test_sqlite_cache_fallback_para_json_se_db_falhar`

---

## TASK-LLM-11 — Model routing (fácil → pequeno, difícil → grande)

**Prioridade:** Baixa
**Esforço:** Alto (3–5 dias)
**Ganho esperado:** 50%+ de redução de custo/tempo mantendo qualidade
**Dev sugerido:** dev3 (Dean)

### Conceito
PRs com título e body claros são classificados corretamente por qualquer modelo. Apenas casos ambíguos precisam de modelos maiores.

```
tinyllama:1.1b  → classificação inicial (rápido/barato)
      ↓ se confidence < threshold
qwen2:1.5b      → reclassificação (confiável)
      ↓ se ainda incerto
groq/llama3-70b → caso extremo (cloud, lento/caro)
```

### O que implementar
- `confidence_score()` em `llm/classifiers.py`: estima confiança pela consistência da saída do modelo (ex: tentativas múltiplas com resultados iguais = alta confiança)
- `RoutingClient` em `llm/client.py`: wrapper que tenta modelo pequeno, escala se necessário

### Testes (TDD)
- `test_routing_client_usa_modelo_pequeno_se_confiante`
- `test_routing_client_escala_para_modelo_maior_se_incerto`

---

## Resumo e priorização

| Task | Prioridade | Esforço | Ganho | Dev | Status |
|---|---|---|---|---|---|
| LLM-01 — Async HTTP (asyncio) | Alta | Médio | 2–4× throughput | dev3 | ✅ concluída |
| LLM-02 — Adaptive batch size | Alta | Baixo | Elimina fallbacks caros | dev3 | ✅ concluída |
| LLM-03 — HTTP keep-alive | Média | Baixo | 5–15% latência | dev3 | ✅ concluída |
| LLM-04 — Heurística pré-classificação | Média | Baixo | 10–30% chamadas | dev2+dev3 | ✅ concluída |
| LLM-05 — Cache de tipo por repo (tools) | Média | Baixo | 33% chamadas | dev4 | ✅ concluída |
| LLM-06 — Métricas + observabilidade | Média | Médio | Diagnóstico | dev3+dev5 | ✅ concluída |
| LLM-07 — Retry com backoff | Média | Baixo | Resiliência | dev3 | ✅ concluída |
| LLM-08 — Benchmark de modelos | Baixa | Médio | Escolha informada | dev3 | ⏳ pendente |
| LLM-09 — Prompt compression | Baixa | Baixo | 10–20% tokens | dev3 | ✅ concluída |
| LLM-10 — SQLite cache | Baixa | Médio | Persistência Docker | dev4 | ✅ concluída |
| LLM-11 — Model routing | Baixa | Alto | Custo/qualidade | dev3 | ⏳ pendente |

### Progresso Sprint 5 (2026-05-25)

✅ **Concluídas**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-09, LLM-10
⏳ **Próximas recomendadas**: LLM-08 (benchmark), LLM-11 (model routing)

```
✅ LLM-02 → ✅ LLM-07 → ✅ LLM-04 → ✅ LLM-01 → ✅ LLM-05+09 → ✅ LLM-03 → ✅ LLM-06 → ✅ LLM-10 → ⏳ LLM-08/11
```

**Nota sobre LLM-01:** Implementado com `asyncio.to_thread()` (stdlib) em vez de `aiohttp`
(não disponível como dependência). O ganho vs `ThreadPoolExecutor` vem do uso de
`asyncio.Semaphore` + `asyncio.gather()` para controle de concorrência mais eficiente.
Função: `enrich_prs_async(prs, client, batch_size, concurrency)` em `llm/classifiers.py`.

---

## Configuração de referência (Sprint 4 — estado atual)

```
# .env — configuração ótima com hardware atual
LLM_BACKEND=ollama
LLM_MODEL=qwen2:1.5b         # ollama pull qwen2:1.5b
LLM_USE_TOOLS=true
LLM_BATCH_SIZE=5
LLM_MAX_WORKERS=4

# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_NUM_PARALLEL=4"
```

**Tempo estimado — 2.000 PRs:** ~12 minutos (primeira execução), ~0s (cache).
