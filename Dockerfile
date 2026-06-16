# ── Build stage ──────────────────────────────────────────────────
# Pinned to a content digest, NOT the floating python:3.12-slim tag,
# so:
#   - GitHub Actions BuildKit's GHA cache cannot serve a stale-digest
#     manifest from a previous CI run (the cache layer attack vector
#     that previously poisoned engine builds with python:3.14-slim).
#   - Docker Hub's mutable 3.12-slim label re-pointing (security
#     patches, distroless rebases) cannot silently shift the build's
#     base bytes between CI runs.
# Digest captured from `docker pull python:3.12-slim` 2026-06-16.
# Both stages share this digest so BuildKit reuses the layer.
# Rotate this digest in lockstep with apt security updates by
# re-running the local pull + commit + bumping the GHA cache scope
# in .github/workflows/ci.yml.
FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9 AS builder

WORKDIR /build

# Copy dependency files first for layer caching. requirements/test.txt
# is intentionally NOT installed - test deps must not ship in the
# runtime image. Audit ref: RD-H1.
COPY requirements/base.txt requirements/base.txt

# Install all pip dependencies first. We do this BEFORE copying src/
# so that this heavy installation step is fully cached by Docker even
# when source code changes.
#
# torch is pinned in requirements/base.txt (security override:
# torch>=2.12.0). We resolve it from the PyTorch CPU index so pip
# picks the CPU-only wheel (~200 MB) rather than the CUDA-bundled
# default from PyPI (~800 MB+). The engine has no GPU code path.
# The previous offline-wheel layer (COPY torch/ /torch_offline/ +
# install /torch_offline/*.whl) is removed because the torch/
# directory is .gitignore'd, never committed, and not provisioned by
# CI, so the COPY broke every build in the workflow build matrix.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=1000 --retries=10 --prefix=/install \
        --extra-index-url https://download.pytorch.org/whl/cpu \
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
#   `requirements/base.txt` step (test deps are intentionally NOT
#   installed in the runtime image - see the build-stage note above).
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
# Runtime stage uses the SAME digest as the builder so the two layers
# share storage in BuildKit's cache and in containerd at the runtime
# pull. Rotating one without the other defeats both the cache-share
# and the reproducibility guarantee.
FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9 AS runtime

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

# RAG knowledge base. The engine's RAG bootstrap (ingest_on_startup=true)
# reads the 9 manifest documents from /app/knowledge at boot
# (knowledgeBaseDir=/app/knowledge; src/engine/rag/ingest/manifest.py
# BOOTSTRAP_MANIFEST). These files live at the repo-root knowledge/ dir
# and are NOT part of the installed Python package, so they must be
# copied explicitly into the runtime image. WORKDIR is /app, so this
# lands at /app/knowledge; the chown below covers ownership for uid 1000.
# Without this, RAG bootstrap fails at ingest with:
#   RAGLoaderError: Cannot load markdown file: /app/knowledge/master_rulebook.md
COPY knowledge/ knowledge/

# Ownership
RUN chown -R etradie:etradie /app /home/etradie

USER etradie

# Pre-bake the SentenceTransformer embedding model into the image so
# the runtime engine pod does NOT need to call HuggingFace at boot.
# The model bytes (~90 MB for sentence-transformers/all-MiniLM-L6-v2)
# live in the etradie user's HF cache, which is mounted at
# /home/etradie/.cache in the runtime pod (chart emptyDir at the same
# path; the COPY ownership above sets the etradie user as owner).
# Without this pre-bake the runtime download stalls on a missing or
# restricted NetworkPolicy egress and /readiness rag.embedding_ready
# stays false until the egress is fixed AND the download completes.
# Pre-bake makes the model load deterministic (~2-3s from disk) and
# air-gap ready. The model name MUST match the runtime config value
# RAG_EMBEDDING_MODEL = all-MiniLM-L6-v2 (helm/engine/values.yaml).
ENV HF_HOME=/home/etradie/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/home/etradie/.cache/torch/sentence_transformers
RUN python -c "from sentence_transformers import SentenceTransformer; \
    m = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
    print('embedding model pre-baked:', m.get_sentence_embedding_dimension(), 'dims')"

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "engine.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--http", "httptools"]

