"""Testes para src/pr_analyzer/llm/system_probe.py — TDD.

Foco nos testes da função PURA recommend_config(). Os testes de
probe_system() usam mocks para isolar I/O de sistema.
"""

import dataclasses
from unittest.mock import patch

import pytest

from pr_analyzer.llm.system_probe import (
    SystemProfile,
    format_report,
    recommend_config,
)

# ── fixtures ──────────────────────────────────────────────────────────────────


def _profile(
    cores: int = 8,
    ram_gb: float = 8.0,
    has_gpu: bool = False,
    vram_gb: float = 0.0,
    ollama: bool = True,
) -> SystemProfile:
    return SystemProfile(
        cpu_logical_cores=cores,
        ram_available_gb=ram_gb,
        has_gpu=has_gpu,
        gpu_vram_gb=vram_gb,
        ollama_running=ollama,
    )


# ── SystemProfile e PipelineConfig são frozen dataclasses ────────────────────


def test_system_profile_e_frozen() -> None:
    profile = _profile()
    assert dataclasses.is_dataclass(profile)
    with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
        profile.cpu_logical_cores = 999  # type: ignore[misc]


def test_pipeline_config_e_frozen() -> None:
    config = recommend_config(_profile(), 0.94)
    assert dataclasses.is_dataclass(config)
    with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
        config.max_workers = 999  # type: ignore[misc]


# ── recommend_config — valores de retorno sempre válidos ─────────────────────


def test_recommend_config_nunca_retorna_zero_workers() -> None:
    profile = _profile(cores=1, ram_gb=0.5)
    config = recommend_config(profile, model_size_gb=4.7)
    assert config.max_workers >= 1


def test_recommend_config_nunca_retorna_zero_batch() -> None:
    profile = _profile(cores=1, ram_gb=0.5)
    config = recommend_config(profile, model_size_gb=4.7)
    assert config.batch_size >= 1


def test_recommend_config_nunca_retorna_zero_parallel() -> None:
    profile = _profile(cores=1, ram_gb=0.5)
    config = recommend_config(profile, model_size_gb=4.7)
    assert config.ollama_num_parallel >= 1


def test_recommend_config_reason_nao_vazio() -> None:
    config = recommend_config(_profile(), 0.94)
    assert isinstance(config.reason, str)
    assert len(config.reason) > 0


# ── use_tools: depende do tamanho do modelo ───────────────────────────────────


def test_recommend_config_use_tools_true_para_qwen2() -> None:
    config = recommend_config(_profile(), model_size_gb=0.94)
    assert config.use_tools is True


def test_recommend_config_use_tools_false_para_tinyllama() -> None:
    config = recommend_config(_profile(), model_size_gb=0.64)
    assert config.use_tools is False


def test_recommend_config_use_tools_true_para_phi3() -> None:
    config = recommend_config(_profile(), model_size_gb=2.2)
    assert config.use_tools is True


# ── CPU: mais cores → mais workers ───────────────────────────────────────────


def test_recommend_config_mais_cores_nao_reduz_workers() -> None:
    cfg_4 = recommend_config(_profile(cores=4), 0.94)
    cfg_16 = recommend_config(_profile(cores=16), 0.94)
    assert cfg_16.max_workers >= cfg_4.max_workers


def test_recommend_config_pouca_ram_limita_parallel() -> None:
    cfg_ok = recommend_config(_profile(cores=16, ram_gb=16.0), 0.94)
    cfg_poor = recommend_config(_profile(cores=16, ram_gb=0.5), 0.94)
    assert cfg_ok.ollama_num_parallel >= cfg_poor.ollama_num_parallel


# ── GPU: permite mais workers e batch maior ───────────────────────────────────


def test_recommend_config_gpu_permite_mais_workers_que_cpu() -> None:
    cpu_cfg = recommend_config(_profile(has_gpu=False), 0.94)
    gpu_cfg = recommend_config(_profile(has_gpu=True, vram_gb=8.0), 0.94)
    assert gpu_cfg.max_workers >= cpu_cfg.max_workers


def test_recommend_config_gpu_6gb_usa_batch_10() -> None:
    config = recommend_config(_profile(has_gpu=True, vram_gb=8.0), 0.94)
    assert config.batch_size >= 10


def test_recommend_config_cpu_usa_batch_5_para_modelo_pequeno() -> None:
    config = recommend_config(_profile(), model_size_gb=0.94)
    assert config.batch_size == 5


def test_recommend_config_cpu_usa_batch_menor_para_modelo_grande() -> None:
    cfg_small = recommend_config(_profile(cores=16, ram_gb=16.0), 0.94)
    cfg_large = recommend_config(_profile(cores=16, ram_gb=16.0), 4.7)
    assert cfg_small.batch_size >= cfg_large.batch_size


# ── parametrize: invariante em qualquer entrada razoável ─────────────────────


@pytest.mark.parametrize("cores", [1, 2, 4, 8, 16, 32])
@pytest.mark.parametrize("ram_gb", [0.5, 2.0, 8.0, 32.0])
@pytest.mark.parametrize("model_gb", [0.35, 0.64, 0.94, 2.2, 4.7])
def test_recommend_config_sempre_retorna_valores_positivos(
    cores: int, ram_gb: float, model_gb: float
) -> None:
    config = recommend_config(_profile(cores=cores, ram_gb=ram_gb), model_gb)
    assert config.max_workers >= 1
    assert config.batch_size >= 1
    assert config.ollama_num_parallel >= 1


# ── format_report ─────────────────────────────────────────────────────────────


def test_format_report_retorna_string_nao_vazia() -> None:
    profile = _profile()
    config = recommend_config(profile, 0.94)
    report = format_report(profile, config)
    assert isinstance(report, str)
    assert len(report) > 0


def test_format_report_menciona_cpu_e_ram() -> None:
    profile = _profile(cores=8, ram_gb=4.35)
    config = recommend_config(profile, 0.94)
    report = format_report(profile, config)
    assert "8" in report
    assert "4" in report


# ── probe_system: testa com mocks de I/O ─────────────────────────────────────


def test_probe_system_retorna_system_profile() -> None:
    from pr_analyzer.llm.system_probe import probe_system

    with (
        patch("pr_analyzer.llm.system_probe._read_ram_gb", return_value=8.0),
        patch("pr_analyzer.llm.system_probe._detect_gpu", return_value=(False, 0.0)),
        patch("pr_analyzer.llm.system_probe._check_ollama", return_value=True),
    ):
        profile = probe_system()

    assert isinstance(profile, SystemProfile)
    assert profile.ram_available_gb == 8.0
    assert profile.has_gpu is False
    assert profile.ollama_running is True


def test_probe_system_detecta_gpu_quando_presente() -> None:
    from pr_analyzer.llm.system_probe import probe_system

    with (
        patch("pr_analyzer.llm.system_probe._read_ram_gb", return_value=16.0),
        patch("pr_analyzer.llm.system_probe._detect_gpu", return_value=(True, 8.0)),
        patch("pr_analyzer.llm.system_probe._check_ollama", return_value=True),
    ):
        profile = probe_system()

    assert profile.has_gpu is True
    assert profile.gpu_vram_gb == 8.0
