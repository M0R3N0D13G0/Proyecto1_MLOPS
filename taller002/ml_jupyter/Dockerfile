FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml ./

RUN uv sync

RUN mkdir -p /app/notebooks /models

EXPOSE 8888

CMD uv run jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --notebook-dir=/app/notebooks \
    --ServerApp.token="${JUPYTER_TOKEN}" \
    --ServerApp.allow_origin="*"
