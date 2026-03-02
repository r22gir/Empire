#!/bin/bash
#############################################
# EmpireBox Portable Test Bundle
# Download and run: bash empire_test_bundle.sh
#############################################

echo "🏰 EmpireBox Environment Test"
echo "=============================="
echo "Date: $(date)"
echo "Host: $(hostname)"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASSED=0
FAILED=0

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; PASSED=$((PASSED+1)); }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; FAILED=$((FAILED+1)); }

echo "=== System Requirements ==="
if command -v python3 &>/dev/null; then pass "Python3 ($(python3 --version 2>&1))"; else fail "Python3 not found"; fi
if command -v node &>/dev/null; then pass "Node.js ($(node --version))"; else fail "Node.js not found"; fi
if command -v npm &>/dev/null; then pass "NPM ($(npm --version))"; else fail "NPM not found"; fi

echo ""
echo "=== Backend Tests ==="
API_URL="${API_URL:-http://localhost:8000}"

if curl -sf "$API_URL/" >/dev/null 2>&1; then pass "API Root ($API_URL/)"; else fail "API Root ($API_URL/)"; fi
if curl -sf "$API_URL/health" >/dev/null 2>&1; then pass "Health endpoint"; else fail "Health endpoint"; fi
if curl -sf "$API_URL/openapi.json" >/dev/null 2>&1; then pass "OpenAPI docs"; else fail "OpenAPI docs"; fi

MAX_RESP=$(curl -sf -X POST "$API_URL/api/v1/max/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"ping","provider":"claude"}' 2>/dev/null || echo "FAIL")
if [[ "$MAX_RESP" != "FAIL" && "$MAX_RESP" != *"error"* ]]; then pass "MAX AI Chat"; else fail "MAX AI Chat"; fi

echo ""
echo "=== Frontend Apps ==="
EMPIRE_DIR="${EMPIRE_DIR:-$HOME/Empire}"

for app in founder_dashboard luxeforge_web contractorforge_web marketf_web; do
    if [[ -d "$EMPIRE_DIR/$app" ]]; then
        pass "$app exists"
        if [[ -f "$EMPIRE_DIR/$app/package.json" ]]; then pass "$app package.json"; else fail "$app package.json"; fi
        if [[ -d "$EMPIRE_DIR/$app/node_modules" ]]; then pass "$app deps installed"; else fail "$app deps missing"; fi
        if [[ -d "$EMPIRE_DIR/$app/.next" ]]; then pass "$app built"; else fail "$app not built"; fi
    else
        fail "$app missing"
    fi
done

echo ""
echo "=== Backend Routers ==="
for r in ai auth economic licenses listings marketplaces messages preorders shipping supportforge_ai supportforge_customers supportforge_kb supportforge_tickets users webhooks; do
    if [[ -f "$EMPIRE_DIR/backend/app/routers/${r}.py" ]]; then pass "Router: $r"; else fail "Router: $r"; fi
done
if [[ -d "$EMPIRE_DIR/backend/app/routers/max" ]]; then pass "Router: max/"; else fail "Router: max/"; fi

echo ""
echo "=============================="
TOTAL=$((PASSED + FAILED))
if [[ $TOTAL -gt 0 ]]; then PCT=$((PASSED * 100 / TOTAL)); else PCT=0; fi
echo "📊 Results: $PASSED passed, $FAILED failed"
echo "📈 Pass rate: ${PCT}%"
echo "=============================="

cat > empire_test_results.json << JSONEOF
{"timestamp":"$(date -Iseconds)","hostname":"$(hostname)","passed":$PASSED,"failed":$FAILED,"pass_rate":"$PCT%"}
JSONEOF
echo "📥 Report saved: empire_test_results.json"
