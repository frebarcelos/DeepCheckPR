FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Atualiza pip e setuptools (necessário para PEP 517 build backend)
RUN pip install --no-cache-dir --upgrade pip setuptools

# Copia pyproject.toml e cria stub mínimo para instalar deps sem precisar do src/ real.
# Assim mudanças em código não invalidam o layer de dependências.
COPY pyproject.toml .
RUN mkdir -p src/pr_analyzer && touch src/pr_analyzer/__init__.py
RUN pip install --no-cache-dir ".[dev]"

# Instala pre-commit hooks (layer separado — só roda se .pre-commit-config.yaml mudar)
COPY .pre-commit-config.yaml .
RUN git init && pre-commit install-hooks || true

# Copia o código real por cima do stub (layer leve, só transferência de arquivos)
COPY src/ src/
COPY . .

EXPOSE 8501

ENV PYTHONPATH=/app/src
ENV OLLAMA_HOST=http://host.docker.internal:11434

CMD ["streamlit", "run", "src/pr_analyzer/ui/app.py", "--server.address=0.0.0.0"]
