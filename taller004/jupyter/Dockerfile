# JupyterLab instalado con uv (mismo patron que taller002/ml_jupyter).
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

RUN mkdir -p /app/notebooks

EXPOSE 8888

CMD uv run --no-sync jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --notebook-dir=/app/notebooks \
    --ServerApp.token="${JUPYTER_TOKEN}"
