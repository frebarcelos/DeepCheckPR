"""Testes para src/pr_analyzer/llm/metrics.py — LLM-06."""

import pytest


def test_fallback_rate_zero_sem_batch_calls() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics()
    assert m.fallback_rate == 0.0


def test_fallback_rate_calculado_corretamente() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics(batch_calls=10, batch_fallbacks=3)
    assert m.fallback_rate == pytest.approx(0.3)


def test_fallback_rate_100_percent() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics(batch_calls=5, batch_fallbacks=5)
    assert m.fallback_rate == pytest.approx(1.0)


def test_throughput_zero_sem_tempo() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics(total_prs=10, total_time_s=0.0)
    assert m.throughput_prs_per_min == 0.0


def test_throughput_calculado_corretamente() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    # 120 PRs em 60 segundos = 120 PRs/min
    m = ClassificationMetrics(total_prs=120, total_time_s=60.0)
    assert m.throughput_prs_per_min == pytest.approx(120.0)


def test_throughput_fracao_de_minuto() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    # 10 PRs em 30 segundos = 20 PRs/min
    m = ClassificationMetrics(total_prs=10, total_time_s=30.0)
    assert m.throughput_prs_per_min == pytest.approx(20.0)


def test_value_counts_inicialmente_vazio() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics()
    assert m.value_counts == {}


def test_record_pr_incrementa_total_prs() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics()
    assert m.total_prs == 0
    m.record_pr("outro", "outro", "insuficiente")
    assert m.total_prs == 1


def test_record_pr_acumula_multiplos_prs() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics()
    for _ in range(5):
        m.record_pr("outro", "outro", "insuficiente")
    assert m.total_prs == 5


def test_value_counts_acumulam_por_campo() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics()
    m.record_pr("biblioteca", "bug fix", "boa")
    m.record_pr("biblioteca", "feature", "boa")
    m.record_pr("framework", "bug fix", "excelente")

    assert m.value_counts["tipo_projeto"]["biblioteca"] == 2
    assert m.value_counts["tipo_projeto"]["framework"] == 1
    assert m.value_counts["natureza"]["bug fix"] == 2
    assert m.value_counts["natureza"]["feature"] == 1
    assert m.value_counts["clareza"]["boa"] == 2
    assert m.value_counts["clareza"]["excelente"] == 1


def test_record_pr_cria_campos_lazy() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics()
    m.record_pr("ferramenta", "refatoração", "básica")

    assert "tipo_projeto" in m.value_counts
    assert "natureza" in m.value_counts
    assert "clareza" in m.value_counts


def test_metrics_campos_padrao_sao_zero() -> None:
    from pr_analyzer.llm.metrics import ClassificationMetrics

    m = ClassificationMetrics()
    assert m.total_prs == 0
    assert m.batch_calls == 0
    assert m.batch_fallbacks == 0
    assert m.individual_calls == 0
    assert m.total_time_s == 0.0
