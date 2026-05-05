.PHONY: setup run test lint build

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
	docker compose --profile test up test
