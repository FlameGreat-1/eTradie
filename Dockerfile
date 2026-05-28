# ── Build stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy dependency files first for layer caching. requirements/test.txt
# is intentionally NOT installed - test deps must not ship in the
# runtime image. Audit ref: RD-H1.
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

# Pre-install the PEP 517 build backends declared in pyproject.toml's
# [build-system].requires into the same /install prefix as the runtime
# deps. Sharing the pip cache mount with the dependency-install step
# above makes this a no-op on warm caches, and the explicit install
# means the next step can disable build isolation without falling back
# to a PyPI roundtrip.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=1000 --retries=10 --prefix=/install \
        "setuptools>=68.0" "wheel>=0.41.0"

# Install the etradie-engine package itself so Python
# resolves 'engine.*' imports natively (no PYTHONPATH hack).
#
# --no-build-isolation: reuse the setuptools/wheel installed above
#   instead of provisioning a fresh PEP 517 build env from PyPI on
#   every rebuild. Without this, an unreachable PyPI fails the build
#   even when nothing has changed.
# --no-deps: runtime deps are already installed by the previous
#   `requirements/base.txt` + `requirements/test.txt` step.
# PYTHONPATH: --no-build-isolation looks for the build backends on
#   sys.path; we installed them into /install via --prefix above, so
#   we must point sys.path there for this RUN step. The path matches
#   the python:3.12-slim base image's site-packages layout.
RUN --mount=type=cache,target=/root/.cache/pip \
    PYTHONPATH=/install/lib/python3.12/site-packages \
    pip install --default-timeout=1000 --retries=10 \
        --no-deps --no-build-isolation \
        --prefix=/install .

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --gid 1000 etradie \
    && useradd --uid 1000 --gid etradie --shell /bin/bash --create-home etradie

# Copy installed packages (includes engine as a proper package)
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy runtime files that are NOT part of the Python package.
# tests/ is intentionally NOT copied into the runtime image; CI runs
# tests inside the build stage or against the source checkout.
# Audit ref: RD-H2.
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

