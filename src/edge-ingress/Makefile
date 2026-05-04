# ============================================================================
# edge-ingress per-service Makefile (THIN REDIRECT)
# ============================================================================
#
# Platform-shared targets (build / test / fmt / clippy / check / clean / ci)
# now live in the top-level Makefile.platform so a single `make help` at the
# repo root prints every contributor-facing target across the polyglot tree.
#
# This file delegates to those top-level targets. Targets that are genuinely
# edge-ingress-specific (run / dev / docker-build / docker-run / bench / doc /
# audit / update) remain implemented here.
#
# Run `make help` from the repo root to see the unified menu.
# ============================================================================

.PHONY: all build build-release release test fmt clippy check clean ci help \
        run dev install bench doc audit update docker-build docker-run

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || cd ../.. && pwd)
CARGO     := cargo
BINARY_NAME := edge-ingress

# ----------------------------------------------------------------------------
# Redirected targets (delegate to top-level Makefile.platform).
# ----------------------------------------------------------------------------

all: build

build: ## (redirect) -> make edge-ingress-build at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-build"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-build

build-release release: ## (redirect) -> make edge-ingress-build-release at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-build-release"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-build-release

test: ## (redirect) -> make edge-ingress-test at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-test"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-test

fmt: ## (redirect) -> make edge-ingress-fmt at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-fmt"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-fmt

clippy: ## (redirect) -> make edge-ingress-clippy at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-clippy"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-clippy

check: ## (redirect) -> make edge-ingress-check at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-check"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-check

clean: ## (redirect) -> make edge-ingress-clean at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-clean"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-clean

ci: ## (redirect) -> make edge-ingress-ci at repo root
	@echo "[edge-ingress/Makefile] redirecting to top-level: make edge-ingress-ci"
	@$(MAKE) -C $(REPO_ROOT) edge-ingress-ci

verify: fmt clippy test ## (legacy) fmt + clippy + test, delegated
	@echo "[edge-ingress/Makefile] verify: all checks passed"

# ----------------------------------------------------------------------------
# Service-local targets (no unified equivalent - run from this directory).
# ----------------------------------------------------------------------------

run: ## Run debug binary locally (CONFIG_PATH=config/config.yaml)
	@echo "Running edge-ingress (debug)..."
	CONFIG_PATH=config/config.yaml $(CARGO) run --bin $(BINARY_NAME)

dev: ## Run with cargo watch auto-reload
	@command -v cargo-watch >/dev/null 2>&1 || { echo "cargo-watch not found. Install with: cargo install cargo-watch"; exit 1; }
	cargo watch -x 'run --bin $(BINARY_NAME)'

install: build-release ## Install release binary via cargo install
	$(CARGO) install --path crates/edge-server

bench: ## Run cargo bench --workspace
	$(CARGO) bench --workspace

doc: ## Generate cargo doc
	$(CARGO) doc --workspace --no-deps --open

audit: ## Run cargo audit (security)
	cargo audit

update: ## cargo update dependencies
	$(CARGO) update

docker-build: ## Build local Docker image (legacy; production uses helm chart)
	@echo "NOTE: production builds the edge-ingress image via CI; this target is for ad-hoc local builds only."
	docker build -t edge-ingress:latest -f $(REPO_ROOT)/deployments/edge-ingress/docker/Dockerfile.edge-ingress $(REPO_ROOT)

docker-run: ## Run the locally-built Docker image
	docker run -p 443:443 -p 9902:9902 edge-ingress:latest

help: ## Show this file's redirect targets (run `make help` at repo root for the full menu)
	@echo ""
	@echo "edge-ingress per-service Makefile (thin redirect)"
	@echo "================================================="
	@echo ""
	@echo "Most targets are redirects to the unified Makefile at the repo root."
	@echo "Run 'make help' from the repo root for the canonical menu."
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
