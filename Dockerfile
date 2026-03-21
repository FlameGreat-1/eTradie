# ── Build stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy dependency files first for layer caching.
COPY torch/ /torch_offline/
COPY requirements/base.txt requirements/base.txt

# Install PyTorch from local wheel + all pip dependencies first!
# We do this BEFORE copying src/, so that this heavy installation
# step is fully cached by Docker even if your source code changes.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=1000 --retries=10 --prefix=/install \
        /torch_offline/*.whl \
        -r requirements/base.txt

# Now copy project files for the package installation
COPY pyproject.toml pyproject.toml
COPY src/ src/

# Install the etradie-engine package itself so Python
# resolves 'engine.*' imports natively (no PYTHONPATH hack).
RUN pip install --no-cache-dir --no-deps --prefix=/install .

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --gid 1000 etradie \
    && useradd --uid 1000 --gid etradie --shell /bin/bash --create-home etradie

# Copy installed packages (includes engine as a proper package)
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy runtime files that are NOT part of the Python package.
COPY alembic.ini alembic.ini
COPY src/engine/shared/db/migrations src/engine/shared/db/migrations

# Ownership
RUN chown -R etradie:etradie /app

USER etradie

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "engine.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--http", "httptools"]

