FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Atualiza pip e setuptools (necessário para PEP 517 build backend)
RUN pip install --no-cache-dir --upgrade pip setuptools

# Copia apenas o necess'ário para instalar dependências (melhor cache de layers)
COPY pyproject.toml .
COPY src/ src/

# Instala dependências — sem -e, não precisa de editable install no container
RUN pip install --no-cache-dir ".[dev]"

# Instala pre-commit hooks
COPY .pre-commit-config.yaml .
RUN git init && pre-commit install-hooks || true

# Copia o restante do projeto
COPY . .

EXPOSE 8501

ENV PYTHONPATH=/app/src
ENV OLLAMA_HOST=http://host.docker.internal:11434

CMD ["streamlit", "run", "src/pr_analyzer/ui/app.py", "--server.address=0.0.0.0"]
