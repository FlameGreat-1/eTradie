#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET="wasm32-wasi"
BUILD_MODE="${1:-release}"

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

verify_magic_bytes() {
    local wasm_file="$1"
    
    log_info "Verifying WASM magic bytes..."
    
    local magic_bytes=$(hexdump -n 4 -e '4/1 "%02x " "\n"' "${wasm_file}")
    
    if [ "${magic_bytes}" = "00 61 73 6d " ]; then
        log_success "Valid WASM magic bytes: ${magic_bytes}"
        return 0
    else
        log_error "Invalid WASM magic bytes: ${magic_bytes} (expected: 00 61 73 6d)"
        return 1
    fi
}

verify_wasm_version() {
    local wasm_file="$1"
    
    log_info "Verifying WASM version..."
    
    local version=$(hexdump -s 4 -n 4 -e '4/1 "%02x " "\n"' "${wasm_file}")
    
    if [ "${version}" = "01 00 00 00 " ]; then
        log_success "Valid WASM version: 1"
        return 0
    else
        log_warn "Unexpected WASM version: ${version}"
        return 0
    fi
}

verify_file_size() {
    local wasm_file="$1"
    local min_size=1024
    local max_size=$((10 * 1024 * 1024))
    
    log_info "Verifying file size..."
    
    local file_size=$(stat -f%z "${wasm_file}" 2>/dev/null || stat -c%s "${wasm_file}")
    
    if [ "${file_size}" -lt "${min_size}" ]; then
        log_error "File too small: ${file_size} bytes (minimum: ${min_size} bytes)"
        return 1
    fi
    
    if [ "${file_size}" -gt "${max_size}" ]; then
        log_error "File too large: ${file_size} bytes (maximum: ${max_size} bytes)"
        return 1
    fi
    
    local human_size=$(numfmt --to=iec-i --suffix=B ${file_size} 2>/dev/null || echo "${file_size} bytes")
    log_success "File size valid: ${human_size}"
    return 0
}

verify_sections() {
    local wasm_file="$1"
    
    log_info "Verifying WASM sections..."
    
    if command -v wasm-objdump &> /dev/null; then
        local sections=$(wasm-objdump -h "${wasm_file}" 2>/dev/null | grep -c "Section" || echo "0")
        if [ "${sections}" -gt 0 ]; then
            log_success "Found ${sections} WASM sections"
        else
            log_warn "Could not detect WASM sections"
        fi
    else
        log_warn "wasm-objdump not found, skipping section verification"
    fi
}

verify_exports() {
    local wasm_file="$1"
    
    log_info "Verifying WASM exports..."
    
    if command -v wasm-objdump &> /dev/null; then
        local exports=$(wasm-objdump -x "${wasm_file}" 2>/dev/null | grep -c "export" || echo "0")
        if [ "${exports}" -gt 0 ]; then
            log_success "Found ${exports} exports"
        else
            log_warn "No exports found"
        fi
    else
        log_warn "wasm-objdump not found, skipping export verification"
    fi
}

verify_integrity() {
    local wasm_file="$1"
    
    log_info "Verifying file integrity..."
    
    if command -v sha256sum &> /dev/null; then
        local checksum=$(sha256sum "${wasm_file}" | awk '{print $1}')
        log_success "SHA256: ${checksum}"
    elif command -v shasum &> /dev/null; then
        local checksum=$(shasum -a 256 "${wasm_file}" | awk '{print $1}')
        log_success "SHA256: ${checksum}"
    else
        log_warn "sha256sum/shasum not found, skipping integrity check"
    fi
}

run_basic_validation() {
    local wasm_file="$1"
    
    log_info "Running basic validation..."
    
    if command -v wasm-validate &> /dev/null; then
        if wasm-validate "${wasm_file}" 2>/dev/null; then
            log_success "WASM validation passed"
        else
            log_error "WASM validation failed"
            return 1
        fi
    else
        log_warn "wasm-validate not found, skipping validation"
    fi
}

generate_report() {
    local wasm_file="$1"
    local report_file="${wasm_file%.wasm}_verification_report.txt"
    
    log_info "Generating verification report..."
    
    {
        echo "WASM Verification Report"
        echo "========================"
        echo "File: ${wasm_file}"
        echo "Date: $(date)"
        echo ""
        echo "File Size: $(stat -f%z "${wasm_file}" 2>/dev/null || stat -c%s "${wasm_file}") bytes"
        echo "SHA256: $(sha256sum "${wasm_file}" 2>/dev/null || shasum -a 256 "${wasm_file}" | awk '{print $1}')"
        echo ""
        echo "Magic Bytes: $(hexdump -n 4 -e '4/1 "%02x " "\n"' "${wasm_file}")"
        echo "Version: $(hexdump -s 4 -n 4 -e '4/1 "%02x " "\n"' "${wasm_file}")"
    } > "${report_file}"
    
    log_success "Report generated: ${report_file}"
}

main() {
    log_info "Starting WASM verification..."
    log_info "Build mode: ${BUILD_MODE}"
    
    local build_dir="${PROJECT_ROOT}/target/${TARGET}"
    if [ "${BUILD_MODE}" = "release" ]; then
        build_dir="${build_dir}/release"
    else
        build_dir="${build_dir}/debug"
    fi
    
    local wasm_file="${build_dir}/etradie_envoy_integration_filter.wasm"
    local optimized_wasm="${build_dir}/etradie_envoy_integration_filter_optimized.wasm"
    
    if [ ! -f "${wasm_file}" ]; then
        log_error "WASM file not found: ${wasm_file}"
        log_info "Run build.sh first to generate WASM binary"
        exit 1
    fi
    
    log_info "Verifying: ${wasm_file}"
    echo ""
    
    local failed=0
    
    verify_magic_bytes "${wasm_file}" || failed=1
    verify_wasm_version "${wasm_file}" || failed=1
    verify_file_size "${wasm_file}" || failed=1
    verify_sections "${wasm_file}" || failed=1
    verify_exports "${wasm_file}" || failed=1
    verify_integrity "${wasm_file}" || failed=1
    run_basic_validation "${wasm_file}" || failed=1
    
    echo ""
    
    if [ -f "${optimized_wasm}" ]; then
        log_info "Verifying optimized binary: ${optimized_wasm}"
        echo ""
        
        verify_magic_bytes "${optimized_wasm}" || failed=1
        verify_wasm_version "${optimized_wasm}" || failed=1
        verify_file_size "${optimized_wasm}" || failed=1
        verify_integrity "${optimized_wasm}" || failed=1
        
        echo ""
    fi
    
    generate_report "${wasm_file}"
    
    if [ "${failed}" -eq 0 ]; then
        log_success "All verifications passed!"
        exit 0
    else
        log_error "Some verifications failed"
        exit 1
    fi
}

main "$@"
