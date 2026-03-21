FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi

COPY . .

EXPOSE 8080

# DigitalOcean App Platform sets PORT; local/docker defaults to 8000
CMD ["sh", "-c", "exec poetry run uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
