#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET="wasm32-wasi"
BUILD_MODE="${1:-release}"
OUTPUT_DIR="${2:-${PROJECT_ROOT}/../../deployments/envoy/kubernetes/base}"

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

encode_base64() {
    local file="$1"
    
    if command -v base64 &> /dev/null; then
        base64 < "${file}" | tr -d '\n'
    else
        log_error "base64 command not found"
        exit 1
    fi
}

generate_configmap() {
    local wasm_file="$1"
    local output_file="$2"
    
    log_info "Encoding WASM binary to base64..."
    
    local encoded=$(encode_base64 "${wasm_file}")
    local file_size=$(stat -f%z "${wasm_file}" 2>/dev/null || stat -c%s "${wasm_file}")
    local human_size=$(numfmt --to=iec-i --suffix=B ${file_size} 2>/dev/null || echo "${file_size} bytes")
    local checksum=$(sha256sum "${wasm_file}" 2>/dev/null || shasum -a 256 "${wasm_file}" | awk '{print $1}')
    
    log_info "Generating ConfigMap manifest..."
    
    cat > "${output_file}" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: etradie-envoy-wasm
  namespace: envoy-system
  labels:
    app: etradie-envoy
    component: wasm-filter
    version: v0.1.0
  annotations:
    description: "Exoper Envoy WASM filter binary"
    build-mode: "${BUILD_MODE}"
    file-size: "${human_size}"
    sha256: "${checksum}"
    generated-at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
data:
  integration-filter.wasm: |
    ${encoded}
EOF
    
    log_success "ConfigMap generated: ${output_file}"
    log_info "Original WASM size: ${human_size}"
    log_info "Base64 encoded size: $(wc -c < "${output_file}" | tr -d ' ') bytes"
    log_info "SHA256: ${checksum}"
}

validate_configmap() {
    local configmap_file="$1"
    
    log_info "Validating ConfigMap..."
    
    if ! grep -q "apiVersion: v1" "${configmap_file}"; then
        log_error "Invalid ConfigMap: missing apiVersion"
        return 1
    fi
    
    if ! grep -q "kind: ConfigMap" "${configmap_file}"; then
        log_error "Invalid ConfigMap: missing kind"
        return 1
    fi
    
    if ! grep -q "integration-filter.wasm:" "${configmap_file}"; then
        log_error "Invalid ConfigMap: missing WASM data"
        return 1
    fi
    
    log_success "ConfigMap validation passed"
}

generate_kustomization_patch() {
    local output_dir="$1"
    local patch_file="${output_dir}/configmap-wasm-patch.yaml"
    
    log_info "Generating Kustomization patch..."
    
    cat > "${patch_file}" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: etradie-envoy-wasm
  namespace: envoy-system
EOF
    
    log_success "Kustomization patch generated: ${patch_file}"
}

main() {
    log_info "Starting ConfigMap generation..."
    log_info "Build mode: ${BUILD_MODE}"
    log_info "Output directory: ${OUTPUT_DIR}"
    
    local build_dir="${PROJECT_ROOT}/target/${TARGET}"
    if [ "${BUILD_MODE}" = "release" ]; then
        build_dir="${build_dir}/release"
    else
        build_dir="${build_dir}/debug"
    fi
    
    local wasm_file="${build_dir}/etradie_envoy_integration_filter.wasm"
    local optimized_wasm="${build_dir}/etradie_envoy_integration_filter_optimized.wasm"
    
    if [ -f "${optimized_wasm}" ] && [ "${BUILD_MODE}" = "release" ]; then
        log_info "Using optimized WASM binary"
        wasm_file="${optimized_wasm}"
    fi
    
    if [ ! -f "${wasm_file}" ]; then
        log_error "WASM file not found: ${wasm_file}"
        log_info "Run build.sh first to generate WASM binary"
        exit 1
    fi
    
    mkdir -p "${OUTPUT_DIR}"
    
    local configmap_file="${OUTPUT_DIR}/configmap-wasm.yaml"
    
    generate_configmap "${wasm_file}" "${configmap_file}"
    validate_configmap "${configmap_file}"
    generate_kustomization_patch "${OUTPUT_DIR}"
    
    log_success "ConfigMap generation completed successfully!"
    log_info "ConfigMap file: ${configmap_file}"
    
    echo ""
    log_info "To apply the ConfigMap:"
    echo "  kubectl apply -f ${configmap_file}"
    echo ""
    log_info "To verify the ConfigMap:"
    echo "  kubectl get configmap etradie-envoy-wasm -n envoy-system"
}

main "$@"
