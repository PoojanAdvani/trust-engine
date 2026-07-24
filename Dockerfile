# syntax=docker/dockerfile:1

# --- Builder stage: install the package into an isolated virtualenv ---
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build into a self-contained venv we can copy into the runtime image.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

# --- Runtime stage: minimal image with just the venv and app config ---
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    TRUST_ENGINE_CONFIG_PATH=/app/config.yaml \
    TRUST_ENGINE_DB_PATH=/data/trust_engine.db

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY config.yaml ./config.yaml

# /data holds the SQLite audit database (mounted as a volume in production).
RUN mkdir -p /data && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

# Serve the app factory; bind to all interfaces so the container is reachable.
CMD ["uvicorn", "trust_engine.api:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
