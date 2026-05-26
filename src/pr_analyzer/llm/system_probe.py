"""Efeito colateral: detecta hardware do sistema e recomenda configuração do pipeline LLM.

Separação clara entre efeitos e lógica pura:
- probe_system(), _read_ram_gb(), _detect_gpu(), _check_ollama() → efeitos (I/O)
- recommend_config()  → função PURA (SystemProfile + float → PipelineConfig)
- format_report()     → função PURA (SystemProfile + PipelineConfig → str)
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Any

# ── Constantes (imutáveis) ────────────────────────────────────────────────────

# Tamanho mínimo (GB) para suporte confiável a tool calling no Ollama.
# 0.8 exclui tinyllama (0.64 GB, sem tools) e inclui qwen2:1.5b (0.87 GB real).
_TOOLS_MIN_SIZE_GB: float = 0.8

# Threads de CPU que uma inferência de LLM consome aproximadamente
_CPU_THREADS_PER_INFERENCE: int = 4


def _model_sizes() -> dict[str, float]:
    """Lookup de tamanho em GB dos modelos mais comuns no Ollama."""
    return {
        "tinyllama": 0.64,
        "tinyllama:1.1b": 0.64,
        "qwen2:0.5b": 0.35,
        "qwen2:1.5b": 0.94,
        "qwen2.5:1.5b": 0.99,
        "phi3:mini": 2.2,
        "phi3.5:mini": 2.2,
        "gemma2:2b": 1.6,
        "llama3.2:1b": 1.3,
        "llama3.2:3b": 2.0,
        "llama3": 4.7,
        "llama3:8b": 4.7,
        "llama3.1": 4.7,
        "mistral": 4.1,
    }


# ── Tipos de dados ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SystemProfile:
    """Snapshot imutável das capacidades do hardware detectado."""

    cpu_logical_cores: int
    ram_available_gb: float
    has_gpu: bool
    gpu_vram_gb: float
    ollama_running: bool


@dataclass(frozen=True)
class PipelineConfig:
    """Configuração recomendada para o pipeline de classificação LLM."""

    max_workers: int
    batch_size: int
    ollama_num_parallel: int
    use_tools: bool
    reason: str


# ── Funções de efeito colateral (I/O) ────────────────────────────────────────


def _read_ram_gb() -> float:
    """Lê RAM disponível em GB via psutil (preferido) ou /proc/meminfo."""
    try:
        import psutil  # type: ignore[import-untyped,unused-ignore]

        return float(psutil.virtual_memory().available) / 1024**3
    except ImportError:
        pass
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 4.0  # fallback conservador


def _detect_gpu() -> tuple[bool, float]:
    """Detecta GPU NVIDIA via nvidia-smi. Retorna (has_gpu, vram_total_gb)."""
    try:
        out = (
            subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            .decode()
            .strip()
        )
        vram_mb = sum(int(x) for x in out.splitlines() if x.strip().isdigit())
        return (vram_mb > 0, vram_mb / 1024)
    except Exception:
        return (False, 0.0)


def _check_ollama(host: str = "") -> bool:
    """Verifica se o Ollama está acessível no host configurado."""
    import urllib.request

    h = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{h}/api/version", timeout=3) as resp:
            return bool(resp.status == 200)
    except Exception:
        return False


def get_model_size_gb(model: str, host: str = "") -> float:
    """Obtém tamanho real do modelo via API Ollama; usa lookup estático como fallback.

    Args:
        model: nome do modelo (ex: "qwen2:1.5b", "llama3").
        host: host do Ollama (usa OLLAMA_HOST do env se vazio).

    Returns:
        Tamanho estimado em GB.
    """
    import json
    import urllib.request

    h = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{h}/api/tags", timeout=5) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
        for m in data.get("models", []):
            name: str = m.get("name", "")
            if name == model or name.startswith(model.split(":")[0] + ":"):
                size_bytes: int = m.get("size", 0)
                if size_bytes > 0:
                    return size_bytes / 1024**3
    except Exception:
        pass

    sizes = _model_sizes()
    model_lower = model.lower()
    if model_lower in sizes:
        return sizes[model_lower]
    base = model_lower.split(":")[0]
    for key, size in sizes.items():
        if key.startswith(base):
            return size
    return 4.0  # fallback conservador (assume modelo grande → menos paralelismo)


def probe_system() -> SystemProfile:
    """Coleta CPU, RAM disponível, GPU e disponibilidade do Ollama.

    Função de efeito colateral — chama I/O do sistema. Em testes, use mocks
    para _read_ram_gb, _detect_gpu e _check_ollama.
    """
    has_gpu, vram_gb = _detect_gpu()
    return SystemProfile(
        cpu_logical_cores=os.cpu_count() or 1,
        ram_available_gb=_read_ram_gb(),
        has_gpu=has_gpu,
        gpu_vram_gb=vram_gb,
        ollama_running=_check_ollama(),
    )


# ── Funções puras (sem I/O) ───────────────────────────────────────────────────


def recommend_config(profile: SystemProfile, model_size_gb: float) -> PipelineConfig:
    """Calcula configuração ótima do pipeline dado o perfil do sistema e modelo.

    Função PURA: sem I/O, sem estado global. Totalmente testável sem mocks.

    Heurísticas aplicadas:
    - GPU: limite por VRAM disponível; pode ter workers além do parallel (GPU é rápida)
    - CPU: 1 worker por _CPU_THREADS_PER_INFERENCE cores; limitado também por RAM
    - use_tools: só para modelos >= _TOOLS_MIN_SIZE_GB (tinyllama não suporta)
    - batch_size: 5 para modelos < 2 GB; 3 para maiores (menos confiáveis em arrays)

    Args:
        profile: snapshot imutável do hardware detectado.
        model_size_gb: tamanho do modelo em GB (peso em RAM durante inferência).

    Returns:
        PipelineConfig com valores garantidamente >= 1.
    """
    use_tools = model_size_gb >= _TOOLS_MIN_SIZE_GB

    if profile.has_gpu and profile.gpu_vram_gb >= model_size_gb:
        parallel = max(1, min(int(profile.gpu_vram_gb // max(model_size_gb, 0.1)), 6))
        workers = min(parallel * 2, 12)
        batch = 10 if profile.gpu_vram_gb >= 6 else 5
        reason = (
            f"GPU detectada ({profile.gpu_vram_gb:.1f} GB VRAM): "
            f"{parallel} instâncias Ollama, {workers} workers, batch={batch}"
        )
    else:
        by_cpu = max(1, profile.cpu_logical_cores // _CPU_THREADS_PER_INFERENCE)
        by_ram = max(1, int(profile.ram_available_gb // max(model_size_gb, 0.1)))
        parallel = max(1, min(by_cpu, by_ram, 4))
        workers = parallel
        batch = 5 if model_size_gb < 2.0 else 3
        reason = (
            f"CPU {profile.cpu_logical_cores} cores, "
            f"{profile.ram_available_gb:.1f} GB RAM: "
            f"{parallel} workers paralelos, batch={batch}"
            + ("" if use_tools else " (tools desabilitado: modelo muito pequeno)")
        )

    return PipelineConfig(
        max_workers=workers,
        batch_size=batch,
        ollama_num_parallel=parallel,
        use_tools=use_tools,
        reason=reason,
    )


def format_report(profile: SystemProfile, config: PipelineConfig) -> str:
    """Formata relatório legível do sistema e configuração recomendada.

    Função PURA — sem I/O.
    """
    gpu_line = (
        f"GPU {config.ollama_num_parallel}x ({profile.gpu_vram_gb:.1f} GB VRAM)"
        if profile.has_gpu
        else "sem GPU (inferência CPU)"
    )
    return (
        f"Sistema detectado:\n"
        f"  CPU: {profile.cpu_logical_cores} cores lógicos\n"
        f"  RAM: {profile.ram_available_gb:.1f} GB disponível\n"
        f"  GPU: {gpu_line}\n"
        f"  Ollama: {'online' if profile.ollama_running else 'offline'}\n"
        f"\n"
        f"Configuração recomendada:\n"
        f"  LLM_MAX_WORKERS={config.max_workers}\n"
        f"  LLM_BATCH_SIZE={config.batch_size}\n"
        f"  LLM_USE_TOOLS={'true' if config.use_tools else 'false'}\n"
        f"  OLLAMA_NUM_PARALLEL={config.ollama_num_parallel}  ← definir no systemd\n"
        f"\n"
        f"  {config.reason}"
    )


def load_pipeline_config() -> dict[str, int | bool]:
    """Retorna configuração do pipeline lendo env; auto-detecta se LLM_MAX_WORKERS=auto.

    Quando LLM_MAX_WORKERS=auto, executa probe_system() + recommend_config()
    e usa os valores calculados como padrão para as demais variáveis não definidas.
    Variáveis definidas explicitamente no env sempre têm prioridade.
    """
    auto = os.environ.get("LLM_MAX_WORKERS", "1").lower() == "auto"

    if auto:
        profile = probe_system()
        model = os.environ.get("LLM_MODEL", "llama3")
        model_size = get_model_size_gb(model)
        cfg = recommend_config(profile, model_size)
        return {
            "max_workers": int(
                os.environ.get("_LLM_WORKERS_OVERRIDE", cfg.max_workers)
            ),
            "batch_size": int(os.environ.get("LLM_BATCH_SIZE", cfg.batch_size)),
            "use_tools": (
                os.environ.get("LLM_USE_TOOLS", "").lower() in ("1", "true", "yes")
                if "LLM_USE_TOOLS" in os.environ
                else cfg.use_tools
            ),
            "ollama_num_parallel": cfg.ollama_num_parallel,
        }

    return {
        "max_workers": int(os.environ.get("LLM_MAX_WORKERS", "1")),
        "batch_size": int(os.environ.get("LLM_BATCH_SIZE", "1")),
        "use_tools": os.environ.get("LLM_USE_TOOLS", "").lower()
        in ("1", "true", "yes"),
        "ollama_num_parallel": 1,
    }
