.PHONY: all build build-release clean test check fmt lint verify help

CARGO := cargo
WASM_TARGET := wasm32-wasi
WASM_OPT := wasm-opt
BUILD_DIR := target/$(WASM_TARGET)/release
WASM_FILE := $(BUILD_DIR)/exoper_envoy_integration_filter.wasm
OPTIMIZED_WASM := $(BUILD_DIR)/exoper_envoy_integration_filter_optimized.wasm

all: build-release

help:
	@echo "Exoper Envoy WASM Filter - Build Targets"
	@echo "=========================================="
	@echo "  make build          - Build debug version"
	@echo "  make build-release  - Build optimized release version"
	@echo "  make test           - Run all tests"
	@echo "  make check          - Run cargo check"
	@echo "  make fmt            - Format code"
	@echo "  make lint           - Run clippy linter"
	@echo "  make verify         - Verify WASM binary"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make all            - Build release (default)"

build:
	@echo "Building debug version..."
	$(CARGO) build --workspace --target $(WASM_TARGET)

build-release:
	@echo "Building release version..."
	$(CARGO) build --workspace --target $(WASM_TARGET) --release
	@echo "Optimizing WASM binary..."
	@if command -v $(WASM_OPT) >/dev/null 2>&1; then \
		$(WASM_OPT) -Oz --strip-debug --strip-producers \
			$(WASM_FILE) -o $(OPTIMIZED_WASM); \
		echo "Optimized WASM: $(OPTIMIZED_WASM)"; \
		ls -lh $(OPTIMIZED_WASM); \
	else \
		echo "wasm-opt not found, skipping optimization"; \
		echo "Install with: cargo install wasm-opt"; \
	fi

test:
	@echo "Running tests..."
	$(CARGO) test --workspace

test-verbose:
	@echo "Running tests (verbose)..."
	$(CARGO) test --workspace -- --nocapture

check:
	@echo "Running cargo check..."
	$(CARGO) check --workspace --target $(WASM_TARGET)

fmt:
	@echo "Formatting code..."
	$(CARGO) fmt --all

fmt-check:
	@echo "Checking code formatting..."
	$(CARGO) fmt --all -- --check

lint:
	@echo "Running clippy..."
	$(CARGO) clippy --workspace --target $(WASM_TARGET) -- -D warnings

lint-fix:
	@echo "Running clippy with auto-fix..."
	$(CARGO) clippy --workspace --target $(WASM_TARGET) --fix --allow-dirty

verify: build-release
	@echo "Verifying WASM binary..."
	@if [ -f $(OPTIMIZED_WASM) ]; then \
		echo "Checking magic bytes..."; \
		hexdump -C $(OPTIMIZED_WASM) | head -n 1 | grep -q "00 61 73 6d" && \
			echo "✓ Valid WASM magic bytes" || \
			echo "✗ Invalid WASM magic bytes"; \
		echo "File size:"; \
		ls -lh $(OPTIMIZED_WASM); \
	elif [ -f $(WASM_FILE) ]; then \
		echo "Checking magic bytes..."; \
		hexdump -C $(WASM_FILE) | head -n 1 | grep -q "00 61 73 6d" && \
			echo "✓ Valid WASM magic bytes" || \
			echo "✗ Invalid WASM magic bytes"; \
		echo "File size:"; \
		ls -lh $(WASM_FILE); \
	else \
		echo "✗ WASM binary not found"; \
		exit 1; \
	fi

clean:
	@echo "Cleaning build artifacts..."
	$(CARGO) clean
	@rm -f $(OPTIMIZED_WASM)

install-tools:
	@echo "Installing required tools..."
	@command -v rustup >/dev/null 2>&1 || { echo "rustup not found. Install from https://rustup.rs/"; exit 1; }
	rustup target add $(WASM_TARGET)
	rustup component add rustfmt clippy
	@echo "Installing wasm-opt..."
	@cargo install wasm-opt || echo "Failed to install wasm-opt"

ci: fmt-check lint test build-release verify
	@echo "✓ All CI checks passed"

watch:
	@echo "Watching for changes..."
	@command -v cargo-watch >/dev/null 2>&1 || { echo "cargo-watch not found. Install with: cargo install cargo-watch"; exit 1; }
	cargo watch -x 'build --target $(WASM_TARGET)'

size-report: build-release
	@echo "WASM Binary Size Report"
	@echo "======================="
	@if [ -f $(OPTIMIZED_WASM) ]; then \
		echo "Optimized:"; \
		ls -lh $(OPTIMIZED_WASM) | awk '{print $$5 " " $$9}'; \
	fi
	@if [ -f $(WASM_FILE) ]; then \
		echo "Unoptimized:"; \
		ls -lh $(WASM_FILE) | awk '{print $$5 " " $$9}'; \
	fi

bench:
	@echo "Running benchmarks..."
	$(CARGO) bench --workspace

doc:
	@echo "Generating documentation..."
	$(CARGO) doc --workspace --no-deps --target $(WASM_TARGET)

doc-open:
	@echo "Generating and opening documentation..."
	$(CARGO) doc --workspace --no-deps --target $(WASM_TARGET) --open
