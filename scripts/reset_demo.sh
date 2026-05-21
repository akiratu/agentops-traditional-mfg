#!/bin/bash
# Reset the live demo to a fresh, predictable state in ~20 seconds.
# Run this before each live demo (or when an audience question makes the
# state confusing).
#
# What it does:
#   1. Removes ALL factory/agent/skill/signal/finding/regression rows
#   2. Re-seeds the 3 government-plan domains
#   3. Pre-presses Accept on the metal-mfg finding and waits ~4 min for
#      Self-Evolve to produce v2 (so the demo can show v1+v2 without waiting).
#      v2 is left as DRAFT so the demo can end with "click Promote" as the
#      live interaction moment — v1 ACTIVE / v2 DRAFT side-by-side, ready for
#      the human-in-loop ceremony.
#
# Output: the URLs to open for the demo.
#
# Prereqs:
#   - Backend running on :8000 with LLM_PROVIDER_NAME=google + GEMINI_API_KEY
#   - Postgres container running (agentops-postgres)
#   - Langfuse running on :3000

set -e

REPO="/Users/akiratu/Downloads/claude code/agentops-traditional-mfg"
BACKEND="${BACKEND:-http://localhost:8000}"

cd "$REPO"

echo "[1/4] Reset DB to empty state..."
docker exec agentops-postgres psql -U agentops -d agentops -c "
UPDATE agent SET current_skill_id = NULL;
DELETE FROM regression_run;
DELETE FROM rca_finding;
DELETE FROM anomaly_signal;
DELETE FROM sop_source;
DELETE FROM skill;
DELETE FROM agent;
DELETE FROM factory;
" > /dev/null

echo "[2/4] Re-seed 3 government-plan domains..."
python3 scripts/seed_three_domains_for_ui.py 2>&1 | tail -5

echo ""
echo "[3/4] Pre-press Accept on metal-mfg finding (so v2 is ready by demo time)..."
FID=$(curl -s "$BACKEND/rca-findings" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
AID=$(curl -s "$BACKEND/agents" | python3 -c "import json,sys; [print(a['id']) for a in json.load(sys.stdin) if 'CNC' in a['name']]")
curl -s -X PATCH "$BACKEND/rca-findings/$FID/status" \
  -H 'content-type: application/json' \
  -d '{"status":"accepted"}' > /dev/null
echo "    Accept fired; Self-Evolve running in background (Gemini Pro, ~4 min)"

echo ""
echo "[4/4] Wait for v2 skill (4 min max)..."
for i in $(seq 1 24); do
  sleep 10
  N=$(curl -s "$BACKEND/skills?agent_id=$AID" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
  echo -n "    "; date +%H:%M:%S; printf "      skill count: %s\n" "$N"
  if [ "${N:-0}" -ge 2 ]; then
    # Intentionally leave v2 as DRAFT — the demo's final step is the human
    # pressing "Promote to ACTIVE" on the skill timeline. That's the visible
    # human-in-loop moment, the dramatic close.
    echo ""
    echo "✓ Demo ready. (v2 left as DRAFT so demo can end with the Promote click.)"
    FACT_URL=$(curl -s "$BACKEND/factories" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
    echo ""
    echo "================================================================"
    echo "  打開瀏覽器 demo:"
    echo "================================================================"
    echo "  起點:        http://localhost:3001/factories"
    echo "  3 場域看完之後,深入金屬加工:"
    echo "    Agent:      http://localhost:3001/agents/$AID"
    echo "    Anomaly:    http://localhost:3001/anomalies"
    echo "    Finding:    http://localhost:3001/findings/$FID"
    echo "    Skill diff: http://localhost:3001/skills/$AID"
    echo "    Regression: http://localhost:3001/regression-runs"
    echo "    SOP Upload: http://localhost:3001/sop-upload"
    echo "================================================================"
    exit 0
  fi
done

echo "⚠️  Self-Evolve 沒在 4 分鐘內完成。可能 Gemini API 慢/失敗。"
echo "    手動檢查 backend log: tail -30 /tmp/agentops-backend-gemini.log"
exit 1
