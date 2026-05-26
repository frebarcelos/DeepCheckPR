.PHONY: hooks setup run test lint format docker-build docker-run docker-test pipeline pipeline-all

# Instala apenas pre-commit e os git hooks — mínimo para quem usa Docker
# Pré-requisito (uma vez): sudo apt install pipx && pipx ensurepath
hooks:
	@command -v pipx >/dev/null 2>&1 || { echo "pipx não encontrado. Rode primeiro:\n  sudo apt install pipx && pipx ensurepath\nDepois abra um novo terminal e rode make hooks novamente."; exit 1; }
	pipx install pre-commit || pipx upgrade pre-commit
	pre-commit install
	pre-commit install --hook-type pre-push
	pre-commit install --hook-type commit-msg

# Setup completo para desenvolvimento sem Docker (instala todas as deps localmente)
setup:
	pip install -e ".[dev]"
	pre-commit install
	pre-commit install --hook-type pre-push
	pre-commit install --hook-type commit-msg

run:
	streamlit run src/pr_analyzer/ui/app.py

test:
	pytest tests/ -m "not integration" --tb=short

test-all:
	pytest tests/ --tb=short

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/

docker-build:
	docker compose build

docker-run:
	docker compose up app

docker-test:
	docker compose run --rm -T app python -m pytest tests/ -m "not integration" --tb=short -q --no-header

# Pipeline completo: dataset (CSV ou JSON) → LLM → output.json
# Uso: make pipeline DATASET=data/arquivo.json OUTPUT=output.json LIMIT=100
# Uso: make pipeline-all DATASET=data/arquivo.json OUTPUT=output.json
DATASET ?= $(DATASET_PATH)
OUTPUT  ?= output.json
LIMIT   ?= 100
pipeline:
	docker compose run --rm app python3 scripts/run_pipeline.py "$(DATASET)" "$(OUTPUT)" $(LIMIT)

# Processa TODOS os registros do dataset (limit=0 → sem limite)
# Uso: make pipeline-all DATASET=data/Python.json OUTPUT=output/python_all.json
pipeline-all:
	docker compose run --rm app python3 scripts/run_pipeline.py "$(DATASET)" "$(OUTPUT)" 0
