#!/usr/bin/env bash
# =============================================================================
# eTradie VPS Connection Verification
#
# Run this from the Linux machine after completing VPS setup.
# Tests the full chain: Linux -> VPS firewall -> ZeroMQ EA -> MT5
#
# Usage:
#   ./verify_vps_connection.sh <VPS_IP> [ENGINE_URL] [ZMQ_PORT]
#
# Example:
#   ./verify_vps_connection.sh 203.0.113.50
#   ./verify_vps_connection.sh 203.0.113.50 http://localhost:8000 5555
# =============================================================================

set -euo pipefail

VPS_IP="${1:?Usage: $0 <VPS_IP> [ENGINE_URL] [ZMQ_PORT]}"
ENGINE_URL="${2:-http://localhost:8000}"
ZMQ_PORT="${3:-5555}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  eTradie VPS Connection Verification${NC}"
echo -e "${CYAN}  $(date -u '+%Y-%m-%d %H:%M:%S UTC')${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
echo "  VPS IP:     $VPS_IP"
echo "  ZMQ Port:   $ZMQ_PORT"
echo "  Engine URL: $ENGINE_URL"
echo ""

PASSED=0
FAILED=0

check() {
    local label="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo -e "  ${GREEN}[PASS]${NC} $label"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}[FAIL]${NC} $label"
        FAILED=$((FAILED + 1))
    fi
}

# -----------------------------------------------------------------------
# Test 1: TCP connectivity to VPS port
# -----------------------------------------------------------------------
echo -e "${CYAN}--- Network Connectivity ---${NC}"
if command -v nc &>/dev/null; then
    nc -zw5 "$VPS_IP" "$ZMQ_PORT" 2>/dev/null
    check "TCP connection to $VPS_IP:$ZMQ_PORT" $?
elif command -v timeout &>/dev/null; then
    timeout 5 bash -c "echo >/dev/tcp/$VPS_IP/$ZMQ_PORT" 2>/dev/null
    check "TCP connection to $VPS_IP:$ZMQ_PORT" $?
else
    echo -e "  ${YELLOW}[SKIP]${NC} No nc or timeout available for TCP test"
fi

# -----------------------------------------------------------------------
# Test 2: Engine health
# -----------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- Engine Health ---${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$ENGINE_URL/health" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    check "Engine /health endpoint" 0
else
    check "Engine /health endpoint (HTTP $HTTP_CODE)" 1
fi

# -----------------------------------------------------------------------
# Test 3: Current broker status
# -----------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- Current Broker Status ---${NC}"
ACTIVE_RESP=$(curl -s "$ENGINE_URL/api/broker/connections/active" 2>/dev/null || echo '{}')
BROKER_CONFIGURED=$(echo "$ACTIVE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('broker_configured', False))" 2>/dev/null || echo "False")
ACTIVE_NAME=$(echo "$ACTIVE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); c=d.get('connection'); print(c.get('name','None') if c else 'None')" 2>/dev/null || echo "None")
echo "  Broker configured: $BROKER_CONFIGURED"
echo "  Active connection: $ACTIVE_NAME"

# -----------------------------------------------------------------------
# Test 4: List existing connections
# -----------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- Existing Broker Connections ---${NC}"
CONN_RESP=$(curl -s "$ENGINE_URL/api/broker/connections" 2>/dev/null || echo '{"connections":[]}')
CONN_COUNT=$(echo "$CONN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('count', 0))" 2>/dev/null || echo "0")
echo "  Total connections: $CONN_COUNT"

if [ "$CONN_COUNT" -gt 0 ]; then
    echo "$CONN_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for c in d.get('connections', []):
    status = '\033[0;32mACTIVE\033[0m' if c.get('is_active') else '\033[0;33minactive\033[0m'
    print(f\"    - {c['name']} ({c['connection_type']}) [{c.get('ea_host','N/A')}:{c.get('ea_port','N/A')}] {status}\")
" 2>/dev/null || true
fi

# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- Summary ---${NC}"
TOTAL=$((PASSED + FAILED))
if [ "$FAILED" -eq 0 ]; then
    echo -e "  ${GREEN}All $TOTAL checks passed.${NC}"
else
    echo -e "  ${YELLOW}$PASSED passed, $FAILED failed out of $TOTAL checks.${NC}"
fi

echo ""
echo -e "${CYAN}--- Next Steps ---${NC}"
echo "  To create a VPS EA connection:"
echo ""
echo "  curl -X POST $ENGINE_URL/api/broker/connections \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{"
echo "      \"connection_type\": \"ea\","
echo "      \"name\": \"VPS EA - Contabo\","
echo "      \"ea_host\": \"$VPS_IP\","
echo "      \"ea_port\": $ZMQ_PORT,"
echo "      \"ea_auth_token\": \"<YOUR_AUTH_TOKEN>\","
echo "      \"mt5_server\": \"<YOUR_BROKER_SERVER>\","
echo "      \"mt5_login\": \"<YOUR_MT5_LOGIN>\","
echo "      \"activate\": true"
echo "    }'"
echo ""

exit $FAILED
