FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python antes de copiar o código (melhor cache)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Instala pre-commit hooks
COPY .pre-commit-config.yaml .
RUN git init && pre-commit install-hooks || true

# Copia o restante do projeto
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "src/pr_analyzer/ui/app.py", "--server.address=0.0.0.0"]
