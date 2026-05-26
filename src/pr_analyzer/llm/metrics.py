"""Métricas de qualidade e observabilidade para o pipeline de classificação LLM.

LLM-06: ClassificationMetrics acumula estatísticas durante enrich_prs().
Nota: não é thread-safe para escrita concorrente (max_workers > 1);
use para diagnóstico onde pequenas imprecisões nos contadores são aceitáveis.
"""

from dataclasses import dataclass, field


@dataclass
class ClassificationMetrics:
    """Acumula estatísticas de uma execução do pipeline LLM.

    Campos acumulados em cada run de enrich_prs():
    - total_prs: número de PRs enriquecidos.
    - batch_calls: total de chamadas batch ao LLM tentadas.
    - batch_fallbacks: batch_calls que levantaram exceção (falhas de batch).
    - individual_calls: chamadas individuais ao LLM (modo tools, batch_size=1).
    - total_time_s: tempo total de enrich_prs() em segundos.
    - value_counts: distribuição de valores por campo de classificação.
    """

    total_prs: int = 0
    cache_hits: int = 0
    batch_calls: int = 0
    batch_fallbacks: int = 0
    individual_calls: int = 0
    total_time_s: float = 0.0
    value_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def fallback_rate(self) -> float:
        """Proporção de chamadas batch que falharam (0.0 se sem chamadas batch)."""
        return self.batch_fallbacks / self.batch_calls if self.batch_calls else 0.0

    @property
    def throughput_prs_per_min(self) -> float:
        """PRs processados por minuto (0.0 se total_time_s == 0)."""
        return (self.total_prs / self.total_time_s * 60) if self.total_time_s else 0.0

    def record_pr(self, project_type: str, nature: str, clarity: str) -> None:
        """Registra classificação de 1 PR em value_counts e incrementa total_prs."""
        for fname, val in (
            ("tipo_projeto", project_type),
            ("natureza", nature),
            ("clareza", clarity),
        ):
            bucket = self.value_counts.setdefault(fname, {})
            bucket[val] = bucket.get(val, 0) + 1
        self.total_prs += 1
