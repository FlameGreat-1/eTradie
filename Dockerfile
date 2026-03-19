# ── Build stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY torch/ /torch_offline/
COPY requirements/base.txt requirements/base.txt

# Install the massive local PyTorch wheel ALONGSIDE the requirements
# so Pip resolves them perfectly together and skips PyPI for torch
RUN pip install --no-cache-dir --prefix=/install /torch_offline/*.whl -r requirements/base.txt

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --gid 1000 etradie \
    && useradd --uid 1000 --gid etradie --shell /bin/bash --create-home etradie

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy source
COPY src/ src/
COPY alembic.ini alembic.ini

# Ownership
RUN chown -R etradie:etradie /app

USER etradie

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "engine.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--http", "httptools"]
