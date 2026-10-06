# Servidor de tracking de MLflow instalado con uv.
# El comando de arranque (backend store, bucket, allowed-hosts) esta en docker-compose.yaml.
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

EXPOSE 5000
