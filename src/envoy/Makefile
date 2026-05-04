# ============================================================================
# envoy per-service Makefile (THIN REDIRECT)
# ============================================================================
#
# Platform-shared targets (build / test / fmt / clippy / verify / clean / ci /
# install-tools) now live in the top-level Makefile.platform so a single
# `make help` at the repo root prints every contributor-facing target across
# the polyglot tree.
#
# This file delegates to those top-level targets. Targets that are genuinely
# envoy-WASM-specific (bench / doc / size-report / watch / lint-fix /
# test-verbose) remain implemented here.
#
# Run `make help` from the repo root to see the unified menu.
# ============================================================================

.PHONY: all build build-release test test-verbose fmt fmt-check lint lint-fix \
        clippy verify check clean ci install-tools help \
        bench doc doc-open size-report watch

REPO_ROOT   := $(shell git rev-parse --show-toplevel 2>/dev/null || cd ../.. && pwd)
CARGO       := cargo
WASM_TARGET := wasm32-wasi
BUILD_DIR   := target/$(WASM_TARGET)/release
WASM_FILE   := $(BUILD_DIR)/etradie_envoy_integration_filter.wasm
OPTIMIZED_WASM := $(BUILD_DIR)/etradie_envoy_integration_filter_optimized.wasm

# ----------------------------------------------------------------------------
# Redirected targets (delegate to top-level Makefile.platform).
# ----------------------------------------------------------------------------

all: build-release

build: ## (redirect) -> make envoy-build-debug at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-build-debug"
	@$(MAKE) -C $(REPO_ROOT) envoy-build-debug

build-release: ## (redirect) -> make envoy-build at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-build"
	@$(MAKE) -C $(REPO_ROOT) envoy-build

test: ## (redirect) -> make envoy-test at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-test"
	@$(MAKE) -C $(REPO_ROOT) envoy-test

fmt: ## (redirect) -> make envoy-fmt at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-fmt"
	@$(MAKE) -C $(REPO_ROOT) envoy-fmt

fmt-check: ## (redirect) -> make envoy-fmt-check at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-fmt-check"
	@$(MAKE) -C $(REPO_ROOT) envoy-fmt-check

lint: ## (redirect) -> make envoy-clippy at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-clippy"
	@$(MAKE) -C $(REPO_ROOT) envoy-clippy

clippy: lint

verify: ## (redirect) -> make envoy-verify at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-verify"
	@$(MAKE) -C $(REPO_ROOT) envoy-verify

check: ## cargo check --workspace --target wasm32-wasi (no unified equivalent today)
	$(CARGO) check --workspace --target $(WASM_TARGET)

clean: ## (redirect) -> make envoy-clean at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-clean"
	@$(MAKE) -C $(REPO_ROOT) envoy-clean

ci: ## (redirect) -> make envoy-ci at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-ci"
	@$(MAKE) -C $(REPO_ROOT) envoy-ci

install-tools: ## (redirect) -> make envoy-install-tools at repo root
	@echo "[envoy/Makefile] redirecting to top-level: make envoy-install-tools"
	@$(MAKE) -C $(REPO_ROOT) envoy-install-tools

# ----------------------------------------------------------------------------
# Service-local targets (no unified equivalent - run from this directory).
# ----------------------------------------------------------------------------

test-verbose: ## Run tests with --nocapture
	$(CARGO) test --workspace -- --nocapture

lint-fix: ## clippy with auto-fix
	$(CARGO) clippy --workspace --target $(WASM_TARGET) --fix --allow-dirty

bench: ## Run cargo bench --workspace
	$(CARGO) bench --workspace

doc: ## Generate cargo doc (no open)
	$(CARGO) doc --workspace --no-deps --target $(WASM_TARGET)

doc-open: ## Generate and open cargo doc
	$(CARGO) doc --workspace --no-deps --target $(WASM_TARGET) --open

size-report: build-release ## Print WASM binary size report
	@echo "WASM Binary Size Report"
	@echo "======================="
	@if [ -f $(OPTIMIZED_WASM) ]; then echo "Optimized:"; ls -lh $(OPTIMIZED_WASM) | awk '{print $$5 " " $$9}'; fi
	@if [ -f $(WASM_FILE) ]; then echo "Unoptimized:"; ls -lh $(WASM_FILE) | awk '{print $$5 " " $$9}'; fi

watch: ## cargo watch auto-rebuild
	@command -v cargo-watch >/dev/null 2>&1 || { echo "cargo-watch not found. Install with: cargo install cargo-watch"; exit 1; }
	cargo watch -x 'build --target $(WASM_TARGET)'

help: ## Show this file's redirect targets (run `make help` at repo root for the full menu)
	@echo ""
	@echo "envoy per-service Makefile (thin redirect)"
	@echo "=========================================="
	@echo ""
	@echo "Most targets are redirects to the unified Makefile at the repo root."
	@echo "Run 'make help' from the repo root for the canonical menu."
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
