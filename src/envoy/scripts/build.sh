#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET="wasm32-wasi"
BUILD_MODE="${1:-release}"
WASM_OPT="${WASM_OPT:-wasm-opt}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v cargo &> /dev/null; then
        log_error "cargo not found. Install Rust from https://rustup.rs/"
        exit 1
    fi
    
    if ! rustup target list --installed | grep -q "${TARGET}"; then
        log_warn "Target ${TARGET} not installed. Installing..."
        rustup target add "${TARGET}"
    fi
    
    if ! command -v "${WASM_OPT}" &> /dev/null; then
        log_warn "wasm-opt not found. Install with: cargo install wasm-opt"
        log_warn "Continuing without optimization..."
        WASM_OPT=""
    fi
    
    log_success "Dependencies check passed"
}

build_workspace() {
    log_info "Building workspace in ${BUILD_MODE} mode..."
    
    cd "${PROJECT_ROOT}"
    
    if [ "${BUILD_MODE}" = "release" ]; then
        cargo build --workspace --target "${TARGET}" --release
    else
        cargo build --workspace --target "${TARGET}"
    fi
    
    log_success "Workspace build completed"
}

optimize_wasm() {
    local wasm_file="$1"
    local output_file="${wasm_file%.wasm}_optimized.wasm"
    
    if [ -z "${WASM_OPT}" ]; then
        log_warn "Skipping optimization (wasm-opt not available)"
        return 0
    fi
    
    if [ ! -f "${wasm_file}" ]; then
        log_error "WASM file not found: ${wasm_file}"
        return 1
    fi
    
    log_info "Optimizing ${wasm_file}..."
    
    "${WASM_OPT}" -Oz \
        --strip-debug \
        --strip-producers \
        --strip-dwarf \
        "${wasm_file}" \
        -o "${output_file}"
    
    local original_size=$(stat -f%z "${wasm_file}" 2>/dev/null || stat -c%s "${wasm_file}")
    local optimized_size=$(stat -f%z "${output_file}" 2>/dev/null || stat -c%s "${output_file}")
    local reduction=$((100 - (optimized_size * 100 / original_size)))
    
    log_success "Optimized: ${output_file}"
    log_info "Original size: $(numfmt --to=iec-i --suffix=B ${original_size} 2>/dev/null || echo ${original_size})"
    log_info "Optimized size: $(numfmt --to=iec-i --suffix=B ${optimized_size} 2>/dev/null || echo ${optimized_size})"
    log_info "Size reduction: ${reduction}%"
}

verify_wasm() {
    local wasm_file="$1"
    
    if [ ! -f "${wasm_file}" ]; then
        log_error "WASM file not found: ${wasm_file}"
        return 1
    fi
    
    log_info "Verifying ${wasm_file}..."
    
    local magic_bytes=$(hexdump -n 4 -e '4/1 "%02x " "\n"' "${wasm_file}")
    if [ "${magic_bytes}" != "00 61 73 6d " ]; then
        log_error "Invalid WASM magic bytes: ${magic_bytes}"
        return 1
    fi
    
    log_success "WASM verification passed"
}

main() {
    log_info "Starting eTradie Envoy WASM build..."
    log_info "Build mode: ${BUILD_MODE}"
    log_info "Target: ${TARGET}"
    
    check_dependencies
    build_workspace
    
    local build_dir="${PROJECT_ROOT}/target/${TARGET}"
    if [ "${BUILD_MODE}" = "release" ]; then
        build_dir="${build_dir}/release"
    else
        build_dir="${build_dir}/debug"
    fi
    
    local wasm_file="${build_dir}/etradie_envoy_integration_filter.wasm"
    
    if [ -f "${wasm_file}" ]; then
        verify_wasm "${wasm_file}"
        
        if [ "${BUILD_MODE}" = "release" ]; then
            optimize_wasm "${wasm_file}"
        fi
    else
        log_error "WASM binary not found at: ${wasm_file}"
        exit 1
    fi
    
    log_success "Build completed successfully!"
    log_info "WASM binary location: ${wasm_file}"
    
    if [ "${BUILD_MODE}" = "release" ] && [ -n "${WASM_OPT}" ]; then
        log_info "Optimized binary: ${wasm_file%.wasm}_optimized.wasm"
    fi
}

main "$@"
