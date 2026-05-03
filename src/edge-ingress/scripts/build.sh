#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

echo "========================================="
echo "Edge-Ingress Build Script"
echo "========================================="
echo "Build Date:   ${BUILD_DATE}"
echo "Git Commit:   ${GIT_COMMIT}"
echo "Git Branch:   ${GIT_BRANCH}"
echo "Project Root: ${PROJECT_ROOT}"
echo "========================================="

cd "${PROJECT_ROOT}"

echo "Checking Rust toolchain..."
if ! command -v cargo &> /dev/null; then
    echo "Error: cargo not found. Please install Rust."
    exit 1
fi

RUST_VERSION=$(rustc --version)
echo "Rust version: ${RUST_VERSION}"

echo "Running cargo check..."
cargo check --workspace --all-targets

echo "Running tests..."
cargo test --workspace --release

echo "Running clippy..."
cargo clippy --workspace --all-targets --release -- -D warnings

echo "Building release binary..."
BUILD_DATE="${BUILD_DATE}" \
GIT_COMMIT="${GIT_COMMIT}" \
cargo build --release --bin edge-ingress

BINARY_PATH="${PROJECT_ROOT}/target/release/edge-ingress"

if [ -f "${BINARY_PATH}" ]; then
    BINARY_SIZE=$(du -h "${BINARY_PATH}" | cut -f1)
    echo "========================================="
    echo "Build successful!"
    echo "Binary: ${BINARY_PATH}"
    echo "Size:   ${BINARY_SIZE}"
    echo "========================================="
else
    echo "Error: Binary not found at ${BINARY_PATH}"
    exit 1
fi

echo "Stripping debug symbols..."
strip "${BINARY_PATH}" 2>/dev/null || true

STRIPPED_SIZE=$(du -h "${BINARY_PATH}" | cut -f1)
echo "Stripped size: ${STRIPPED_SIZE}"

echo "Build complete!"
