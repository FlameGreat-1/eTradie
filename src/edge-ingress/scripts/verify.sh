#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BINARY_PATH="${PROJECT_ROOT}/target/release/edge-ingress"

echo "========================================="
echo "Edge-Ingress Binary Verification"
echo "========================================="

if [ ! -f "${BINARY_PATH}" ]; then
    echo "Error: Binary not found at ${BINARY_PATH}"
    echo "Run 'make release' or './scripts/build.sh' first."
    exit 1
fi

echo "Binary path: ${BINARY_PATH}"

if [ ! -x "${BINARY_PATH}" ]; then
    echo "Error: Binary is not executable"
    exit 1
fi

echo "✓ Binary is executable"

BINARY_SIZE=$(du -h "${BINARY_PATH}" | cut -f1)
echo "Binary size: ${BINARY_SIZE}"

if command -v file &> /dev/null; then
    FILE_TYPE=$(file "${BINARY_PATH}")
    echo "File type: ${FILE_TYPE}"
fi

if command -v ldd &> /dev/null; then
    echo ""
    echo "Dynamic library dependencies:"
    ldd "${BINARY_PATH}" || echo "Static binary (no dynamic dependencies)"
fi

echo ""
echo "Testing binary execution..."
if "${BINARY_PATH}" --version &> /dev/null; then
    VERSION_OUTPUT=$("${BINARY_PATH}" --version 2>&1 || echo "Version check not implemented")
    echo "Version: ${VERSION_OUTPUT}"
else
    echo "Warning: Binary does not support --version flag"
fi

echo ""
echo "Checking for required symbols..."
if command -v nm &> /dev/null; then
    SYMBOL_COUNT=$(nm -D "${BINARY_PATH}" 2>/dev/null | wc -l || echo "0")
    echo "Exported symbols: ${SYMBOL_COUNT}"
fi

echo ""
echo "Security checks..."
if command -v checksec &> /dev/null; then
    checksec --file="${BINARY_PATH}"
else
    echo "checksec not available (install pax-utils for security checks)"
fi

echo ""
echo "Generating SHA256 checksum..."
if command -v sha256sum &> /dev/null; then
    SHA256=$(sha256sum "${BINARY_PATH}" | cut -d' ' -f1)
    echo "SHA256: ${SHA256}"
    echo "${SHA256}  edge-ingress" > "${PROJECT_ROOT}/target/release/edge-ingress.sha256"
    echo "Checksum saved to: ${PROJECT_ROOT}/target/release/edge-ingress.sha256"
elif command -v shasum &> /dev/null; then
    SHA256=$(shasum -a 256 "${BINARY_PATH}" | cut -d' ' -f1)
    echo "SHA256: ${SHA256}"
    echo "${SHA256}  edge-ingress" > "${PROJECT_ROOT}/target/release/edge-ingress.sha256"
    echo "Checksum saved to: ${PROJECT_ROOT}/target/release/edge-ingress.sha256"
else
    echo "Warning: sha256sum/shasum not available"
fi

echo ""
echo "========================================="
echo "Verification complete!"
echo "========================================="
