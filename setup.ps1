#!/usr/bin/env pwsh
# Alternativa ao Makefile para Windows 11 sem make instalado.
# Uso:
#   .\setup.ps1 hooks   — instala apenas pre-commit + git hooks (mínimo, para Docker users)
#   .\setup.ps1 setup   — instalação completa sem Docker (padrão se omitido)

param([string]$Target = "setup")

function Install-Hooks {
    Write-Host "Instalando pre-commit e git hooks..." -ForegroundColor Cyan
    pip install pre-commit
    pre-commit install
    pre-commit install --hook-type pre-push
    pre-commit install --hook-type commit-msg
    Write-Host "Hooks instalados!" -ForegroundColor Green
}

if ($Target -eq "hooks") {
    Install-Hooks
}
elseif ($Target -eq "setup") {
    Write-Host "Instalando dependencias completas do projeto..." -ForegroundColor Cyan
    pip install -e ".[dev]"
    Install-Hooks
    Write-Host "Setup concluido!" -ForegroundColor Green
}
else {
    Write-Host "Uso: .\setup.ps1 [hooks|setup]" -ForegroundColor Yellow
    exit 1
}
