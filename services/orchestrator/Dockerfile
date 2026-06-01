# syntax=docker/dockerfile:1.9

FROM python:3.12-slim AS builder
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev || uv sync --no-dev

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/.venv/bin:${PATH}"
RUN groupadd -r app && useradd -r -g app -u 10001 app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
