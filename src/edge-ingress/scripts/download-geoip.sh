#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

GEOIP_DIR="${PROJECT_ROOT}/data/geoip"
GEOIP_DB="${GEOIP_DIR}/GeoLite2-City.mmdb"

MAXMIND_LICENSE_KEY="${MAXMIND_LICENSE_KEY:-}"
MAXMIND_ACCOUNT_ID="${MAXMIND_ACCOUNT_ID:-}"

GEOLITE2_URL="https://download.maxmind.com/app/geoip_download"

echo "========================================="
echo "MaxMind GeoLite2 Database Downloader"
echo "========================================="

if [ -z "${MAXMIND_LICENSE_KEY}" ]; then
    echo "Error: MAXMIND_LICENSE_KEY environment variable not set"
    echo ""
    echo "To download GeoLite2 database, you need a MaxMind account:"
    echo "1. Sign up at https://www.maxmind.com/en/geolite2/signup"
    echo "2. Generate a license key at https://www.maxmind.com/en/accounts/current/license-key"
    echo "3. Set environment variables:"
    echo "   export MAXMIND_ACCOUNT_ID='your_account_id'"
    echo "   export MAXMIND_LICENSE_KEY='your_license_key'"
    echo ""
    echo "Alternatively, download manually:"
    echo "1. Visit https://dev.maxmind.com/geoip/geolite2-free-geolocation-data"
    echo "2. Download GeoLite2-City.mmdb"
    echo "3. Place it at: ${GEOIP_DB}"
    exit 1
fi

mkdir -p "${GEOIP_DIR}"

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "Downloading GeoLite2-City database..."
DOWNLOAD_URL="${GEOLITE2_URL}?edition_id=GeoLite2-City&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz"

if command -v curl &> /dev/null; then
    curl -fsSL "${DOWNLOAD_URL}" -o "${TEMP_DIR}/GeoLite2-City.tar.gz"
elif command -v wget &> /dev/null; then
    wget -q "${DOWNLOAD_URL}" -O "${TEMP_DIR}/GeoLite2-City.tar.gz"
else
    echo "Error: Neither curl nor wget found. Please install one of them."
    exit 1
fi

echo "Extracting database..."
tar -xzf "${TEMP_DIR}/GeoLite2-City.tar.gz" -C "${TEMP_DIR}"

EXTRACTED_DB=$(find "${TEMP_DIR}" -name "GeoLite2-City.mmdb" -type f)

if [ -z "${EXTRACTED_DB}" ]; then
    echo "Error: GeoLite2-City.mmdb not found in downloaded archive"
    exit 1
fi

mv "${EXTRACTED_DB}" "${GEOIP_DB}"

DB_SIZE=$(du -h "${GEOIP_DB}" | cut -f1)
echo ""
echo "========================================="
echo "Download complete!"
echo "Database: ${GEOIP_DB}"
echo "Size:     ${DB_SIZE}"
echo "========================================="

if command -v sha256sum &> /dev/null; then
    SHA256=$(sha256sum "${GEOIP_DB}" | cut -d' ' -f1)
    echo "SHA256: ${SHA256}"
elif command -v shasum &> /dev/null; then
    SHA256=$(shasum -a 256 "${GEOIP_DB}" | cut -d' ' -f1)
    echo "SHA256: ${SHA256}"
fi

echo ""
echo "Database ready for use!"
