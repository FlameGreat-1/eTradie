.PHONY: all build test clean fmt clippy check release install run dev help

CARGO := cargo
BINARY_NAME := edge-ingress
BUILD_DIR := target
RELEASE_DIR := $(BUILD_DIR)/release
DEBUG_DIR := $(BUILD_DIR)/debug

all: build

help:
	@echo "Edge-Ingress Build Targets:"
	@echo "  make build       - Build debug binary"
	@echo "  make release     - Build optimized release binary"
	@echo "  make test        - Run all tests"
	@echo "  make check       - Run cargo check"
	@echo "  make fmt         - Format code"
	@echo "  make clippy      - Run clippy linter"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make run         - Run debug binary"
	@echo "  make dev         - Run with auto-reload (cargo watch)"
	@echo "  make install     - Install release binary"

build:
	@echo "Building debug binary..."
	$(CARGO) build

release:
	@echo "Building release binary..."
	BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
	GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
	$(CARGO) build --release

test:
	@echo "Running tests..."
	$(CARGO) test --workspace

check:
	@echo "Running cargo check..."
	$(CARGO) check --workspace

fmt:
	@echo "Formatting code..."
	$(CARGO) fmt --all

clippy:
	@echo "Running clippy..."
	$(CARGO) clippy --workspace --all-targets -- -D warnings

clean:
	@echo "Cleaning build artifacts..."
	$(CARGO) clean

run:
	@echo "Running debug binary..."
	CONFIG_PATH=config/config.yaml $(CARGO) run --bin $(BINARY_NAME)

dev:
	@echo "Running with auto-reload..."
	cargo watch -x 'run --bin $(BINARY_NAME)'

install: release
	@echo "Installing release binary..."
	$(CARGO) install --path crates/edge-server

bench:
	@echo "Running benchmarks..."
	$(CARGO) bench --workspace

doc:
	@echo "Generating documentation..."
	$(CARGO) doc --workspace --no-deps --open

audit:
	@echo "Running security audit..."
	cargo audit

update:
	@echo "Updating dependencies..."
	$(CARGO) update

verify: fmt clippy test
	@echo "All verification checks passed!"

ci: check clippy test
	@echo "CI checks passed!"

docker-build:
	@echo "Building Docker image..."
	docker build -t edge-ingress:latest .

docker-run:
	@echo "Running Docker container..."
	docker run -p 443:443 -p 9902:9902 edge-ingress:latest
