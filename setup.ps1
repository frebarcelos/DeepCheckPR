#!/usr/bin/env pwsh
# Alternativa ao `make setup` para Windows 11 sem make instalado.
# Uso: .\setup.ps1

Write-Host "Instalando dependencias do projeto..." -ForegroundColor Cyan
pip install -e ".[dev]"

Write-Host "Instalando hooks pre-commit..." -ForegroundColor Cyan
pre-commit install
pre-commit install --hook-type pre-push
pre-commit install --hook-type commit-msg

Write-Host "Setup concluido!" -ForegroundColor Green
