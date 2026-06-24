EXAMINE THE docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md DEEPLY AND THOROUGHLY FROM THE BEGINNING TO THE END SO THAT YOU WILL KNOW THE ISSUES WE ADDRESSED IN PREVIOUS SESSION AS WE ARE STARTING FRESH SESSION.

MAKE SURE YOU EXAMINE CAREFULLY SO THAT YOU WILL GAIN FULLY AND COMPLETE UNDERSTANDING


IT MEANS THAT'S EXACTLY WHAT WE SHOULD BE TRACING IN THE CODEBASE THOROUGHLY TO SEE THE EXACT CAUSE
  
THEREFORE, AS A SENIOR ENGINEER YOU HAVE TO PERFORM A DEEP AND THOROUGH AUDIT ON THE ENTIRE AND WHOLE PIPELINE EXAMINING ALL PLACES AND FILES END TO END ECAUSE WE EED TO AVOID PATCH WORK OR EASY WORK THAT WILL BREAK IN PRODUCTION

WE NEED THE RAW TRUTH OF EXACTLY HOW EVERYTHING AND THE WHOLE PIPELINE OPERATE

DO NOT STOP UNTIL YOU ARE DONE EXAMINING

AVOID ASSUMPTIONS

AVOID GUESSING

YOU MUST BE 100% CERTAIN AND SURE OF EVERY SINGLE THING TO AVOID PROBLEM

DO NOT IGNORE, SKIP OR AVOID EXAMINING ALL PLACES REQUIRED, YOU MUST EXAMINE COMPLETELY

PLEASE NOTE: DO NOT STOP UNTIL YOU ARE DONE EXAMINING ALL & COVERED EVERYTHING

DO NOT DELEGATE TO AGENTS

Every 2.0s: kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-mt-node                                  Softverse: Tue Jun 23 18:19:09 2026

No resources found in etradie-system namespace.




softverse@Softverse:~$ POD=etradie-mt-7b9fd8c0-6a1-0

# Allow it to reach the post-LiveUpdate phase + login attempt
sleep 60

# 1. Pod readiness
kubectl -n etradie-system get pod "$POD"

# 2. The journal — the key signal
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"; \
   f=$(ls -t "$P/logs"/*.log 2>/dev/null | head -1); \
   echo "file: $f, size: $(wc -c < "$f") bytes"; \
   tr -d "\000" < "$f"'

# 3. EA's log (MQL5/Logs)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"; \
   ls -la "$P/MQL5/Logs/" 2>&1 | head -10; \
   f=$(ls -t "$P/MQL5/Logs"/*.log 2>/dev/null | head -1); \
   [ -n "$f" ] && { echo "--- $f ---"; tr -d "\000" < "$f" | tail -60; }'

# 4. :5555 socket state
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

# 5. DB row
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, mt5_symbol, is_active FROM broker_connections WHERE connection_type='hosted';"
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
                  id                  | status |                                status_message                                | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+------------+-----------
 7b9fd8c0-6a1d-44e0-b382-59b06c7a305b | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout |            | t
(1 row)

softverse@Softverse:~$




# ─────────────────────────────────────────────────────────────────────
# Hosted-MT staging verification — paste + typing fallback ship
# Commits: 4d908e4d (fluxbox) + 1c9cfac1 (typing hardening) +
#          d238f60a (paste) + b3a42eaa (typing fallback) + d800f94e (docs)
# ─────────────────────────────────────────────────────────────────────

# ── Step 0: refresh local checkout ───────────────────────────────────
cd ~/eTradie
git fetch origin main
git pull --rebase origin main
git log --oneline -8
# Expect newest first:
#   <ci bump> ci: pin staging image tags to <new-SHA>
#   d800f94e  docs(runbook): rewrite ...
#   b3a42eaa  fix(mt-node): add typing fallback ...
#   d238f60a  fix(mt-node): switch Phase 3 from xdotool type to clipboard paste
#   1c9cfac1  fix(mt-node): Phase 3 keystroke reliability ...
#   ...

# ── Step 1: read pinned mt-node SHA ──────────────────────────────────
PIN=$(git show origin/main:helm/engine/values-staging.yaml \
  | grep -E '^[[:space:]]*tag:' | head -1 | tr -d ' "' | cut -d: -f2)
echo "Pinned mt-node SHA: $PIN"

# ── Step 2: verify image exists on GHCR ──────────────────────────────
GH_OWNER=FlameGreat-1
GH_PAT=$(cat ~/.ghcr_pat)
token=$(curl -sS -u "$GH_OWNER:$GH_PAT" \
  "https://ghcr.io/token?service=ghcr.io&scope=repository:flamegreat-1/etradie/mt-node:pull" \
  | jq -r .token)
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $token" \
  -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
  "https://ghcr.io/v2/flamegreat-1/etradie/mt-node/manifests/$PIN"
# Expect: 200

# ── Step 3: tunnel + ArgoCD sync ─────────────────────────────────────
echo "Confirm tunnel is alive in second terminal, then press Enter."
read -r

export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes

kubectl -n argocd patch application engine-staging --type merge -p '{
  "operation": {"sync": {"revision": "HEAD", "syncOptions": ["Force=true", "Replace=true"]}}
}'
kubectl -n argocd patch application mt-node-staging --type merge -p '{
  "operation": {"sync": {"revision": "HEAD", "syncOptions": ["Force=true", "Replace=true"]}}
}' 2>/dev/null || true

# ── Step 4: engine rollout + env confirm ─────────────────────────────
kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE

# ── Step 5: cleanup ─────────────────────────────────────────────────
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' RETURNING id, status;"

kubectl -n etradie-system delete pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found

for pvc in $(kubectl -n etradie-system get pvc \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  kubectl -n etradie-system patch pvc "$pvc" \
    -p '{"metadata":{"finalizers":null}}' --type=merge
done

ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
for old in $(kubectl -n etradie-system get events --field-selector reason=Killing 2>/dev/null \
  | grep -oE 'etradie-mt-[a-f0-9-]+' | sort -u); do
  timeout 15 kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv metadata delete -mount=etradie \
    "etradie/tenants/mt-node/$old" 2>/dev/null || true
done

kubectl -n etradie-system rollout restart deploy/etradie-engine
kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s

kubectl -n etradie-system get pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status FROM broker_connections WHERE connection_type='hosted';"

echo ""
echo "================================================================"
echo "RE-PROVISION FROM DASHBOARD NOW."
echo "Press Enter the SECOND you click submit."
echo "================================================================"
read -r

# ── Step 6: race to pod ─────────────────────────────────────────────
REL=""
for i in $(seq 1 30); do
  REL=$(kubectl -n etradie-system get statefulset -o name 2>/dev/null \
    | grep 'etradie-mt-' | head -1 | cut -d/ -f2)
  [ -n "$REL" ] && { echo "Release: $REL"; break; }
  echo "waiting for StatefulSet... ($i)"
  sleep 2
done
POD="${REL}-0"
echo "POD=$POD"

for i in $(seq 1 60); do
  state=$(kubectl -n etradie-system get pod "$POD" \
    -o jsonpath='{.status.containerStatuses[?(@.name=="mt-node")].state}' 2>/dev/null)
  echo "[$i] mt-node state: $state"
  echo "$state" | grep -q running && break
  sleep 2
done

kubectl -n etradie-system get pod "$POD" \
  -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'

# ── Step 7: CRITICAL — verify fluxbox + xclip + xdotool installed ───
echo ""
echo "================================================================"
echo "TOOL AVAILABILITY CHECK"
echo "================================================================"
sleep 15
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'which xdotool xclip xprop xwd fluxbox; echo "---"; xclip -version 2>&1 | head -1'

# ── Step 8: verify fluxbox started + EWMH atoms ─────────────────────
echo ""
echo "================================================================"
echo "FLUXBOX + EWMH READINESS"
echo "================================================================"
kubectl -n etradie-system logs "$POD" -c mt-node 2>&1 \
  | grep -iE 'fluxbox|_NET_ACTIVE_WINDOW|auto_login: start|hard-kill' | head -10

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xprop -root _NET_SUPPORTED 2>&1 | tr "," "\n" | grep -iE "_NET_ACTIVE_WINDOW" | head -3'

# ── Step 9: 8-minute poll loop with diagnostic capture ──────────────
mkdir -p ~/phase2c-diagnostics
cd ~/phase2c-diagnostics

P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

for i in $(seq 1 16); do
  echo ""
  echo "============ poll $i / 16  ($(date -u +%H:%M:%S)) ============"
  kubectl -n etradie-system get pod "$POD" --no-headers 2>&1 || { echo "POD GONE"; break; }

  echo ""
  echo "--- driver log (auto_login + paste/type sentinels) ---"
  kubectl -n etradie-system logs "$POD" -c mt-node --tail=400 2>&1 \
    | grep -iE 'auto_login|MetaTrader exited|welcome modal|fluxbox|deliver|paste|type|phase3 stage' \
    | tail -30

  echo ""
  echo "--- :5555 socket state ---"
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

  echo ""
  echo "--- accounts.dat presence ---"
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    "ls -la \"$P/config/accounts.dat\" 2>&1 | head -2"

  # Capture screenshot at polls 4, 8, 12, 16
  if [ "$i" = "4" ] || [ "$i" = "8" ] || [ "$i" = "12" ] || [ "$i" = "16" ]; then
    echo ""
    echo "--- capturing framebuffer (poll $i) ---"
    kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
      'DISPLAY=:99 xwd -root -silent > /tmp/screen.xwd && wc -c /tmp/screen.xwd' 2>/dev/null || true
    kubectl -n etradie-system cp etradie-system/"$POD":/tmp/screen.xwd \
      "./screen-poll-$i.xwd" -c mt-node 2>/dev/null || true
  fi

  sleep 30
done

# ── Step 10: final artifacts ────────────────────────────────────────
echo ""
echo "============ FINAL ARTIFACTS ============"
kubectl -n etradie-system logs "$POD" -c mt-node > driver-log-full.txt 2>&1
wc -l driver-log-full.txt

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log 2>/dev/null | head -1); \
   [ -n \"\$f\" ] && tr -d '\\000' < \"\$f\"" > mt5-journal.txt
echo "mt5-journal.txt: $(wc -l < mt5-journal.txt) lines"

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>&1 | while read wid; do echo "WID=$wid name=$(DISPLAY=:99 xdotool getwindowname "$wid" 2>/dev/null)"; done' \
  > windows-final.txt
cat windows-final.txt

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xwd -root -silent > /tmp/screen-final.xwd && wc -c /tmp/screen-final.xwd'
kubectl -n etradie-system cp etradie-system/"$POD":/tmp/screen-final.xwd ./screen-final.xwd -c mt-node 2>/dev/null

# Convert all screenshots
for f in screen-poll-4 screen-poll-8 screen-poll-12 screen-poll-16 screen-final; do
  [ -s "$f.xwd" ] && convert "$f.xwd" "$f.png" && echo "OK: $f.png"
done

# ── Step 11: verdict ────────────────────────────────────────────────
echo ""
echo "============ VERDICT ============"
kubectl -n etradie-system get pod "$POD"

echo ""
echo "--- accounts.dat (login completed?) ---"
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/config/accounts.dat\" 2>&1"

echo ""
echo "--- MQL5/Logs (EA loaded?) ---"
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/MQL5/Logs/\" 2>&1 | head -5"

echo ""
echo "--- :5555 socket ---"
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

echo ""
echo "--- MT5 journal (broker response is here) ---"
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log 2>/dev/null | head -1); \
   echo \"file: \$f\"; tr -d '\\000' < \"\$f\""

echo ""
echo "--- DB row ---"
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, mt5_symbol, is_active \
   FROM broker_connections WHERE connection_type='hosted';"

echo ""
echo "============ DRIVER SENTINELS ============"
echo ""
echo "--- fluxbox readiness ---"
grep -iE 'fluxbox ready' driver-log-full.txt | head -2

echo ""
echo "--- Welcome modal handling ---"
grep -iE 'welcome modal' driver-log-full.txt | head -5

echo ""
echo "--- Phase 2c (Login dialog open) ---"
grep -iE 'appeared after|all three Phase 2c' driver-log-full.txt | head -5

echo ""
echo "--- Phase 3 strategy + per-field outcome ---"
grep -iE 'deliver |paste |type ' driver-log-full.txt | head -30

echo ""
echo "--- Phase 3 stage transitions ---"
grep -iE 'phase3 stage=' driver-log-full.txt | head -20

echo ""
echo "--- Final outcome ---"
grep -iE 'LISTEN.*exit success|never bound|all three Phase 2c.*failed|hard-kill|exiting|BOTH paste and type failed' driver-log-full.txt | tail -10

echo ""
echo "============ FILES ============"
ls -la ~/phase2c-diagnostics/*.png ~/phase2c-diagnostics/*.txt 2>/dev/null

echo ""
echo "Open these screenshots to visually verify:"
echo "  explorer.exe ~/phase2c-diagnostics/screen-poll-4.png   (early - Login dialog)"
echo "  explorer.exe ~/phase2c-diagnostics/screen-poll-8.png   (mid-Phase-3)"
echo "  explorer.exe ~/phase2c-diagnostics/screen-final.png    (end state)"


