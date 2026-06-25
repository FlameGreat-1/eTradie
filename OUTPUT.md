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





# ─────────────────────────────────────────────────────────────────────
# Hosted-MT staging verification — post-!24 / !25 / !26 merge cycle
#
# Targets this round's two ground-truth questions:
#   (a) Does the recovery loop now correctly skip status='failed' rows?
#       (verified by !25 — fix(hosted-recovery): skip rows in terminal
#        status='failed' state)
#   (b) Does the broker-bundle initContainer + entrypoint.sh install
#       actually deliver Exness servers.dat into $MT_DIR/config/?
#       (verified by !26 — obs(mt-node): deterministic broker-bundle
#        install logging in entrypoint.sh)
#
# Captures evidence at every stage. Saves all artifacts to a timestamped
# directory so previous runs are not overwritten.
# ─────────────────────────────────────────────────────────────────────

set -u

# Timestamped diagnostic dir
TS=$(date -u +%Y%m%dT%H%M%SZ)
DIAG_DIR="$HOME/phase2c-diagnostics/${TS}"
mkdir -p "$DIAG_DIR"
cd "$DIAG_DIR"
echo "Diagnostic dir: $DIAG_DIR"
echo "(All screenshots, logs, and journal captures land here)"

# ────────────────────────────────────────────────────────────────────
# STAGE 0 — confirm CI has built new images
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 0 — confirm latest commits + CI image pin"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

cd ~/eTradie
git fetch origin main
git pull --rebase origin main
git log --oneline -12

echo ""
echo "Confirm the TOP commit is 'ci: pin staging image tags to ...'"
echo "(without that bot commit the CI has not finished building the"
echo "new mt-node + engine images yet — DO NOT PROCEED until you see it)"
echo ""
read -rp "Press Enter ONLY if you confirmed the CI image-pin commit is on top: "

# ────────────────────────────────────────────────────────────────────
# STAGE 1 — read pinned image SHA
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 1 — read pinned image SHAs from values-staging.yaml"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

# Engine + mt-node share the same image tag because both are built
# from the same monorepo by the same CI pipeline.
PIN=$(git show origin/main:helm/engine/values-staging.yaml \
  | grep -E '^[[:space:]]*tag:' | head -1 | tr -d ' "' | cut -d: -f2)
echo "Pinned image SHA (engine + mt-node share the tag): $PIN"
echo "$PIN" > pinned-sha.txt

cd "$DIAG_DIR"

# ────────────────────────────────────────────────────────────────────
# STAGE 2 — verify image exists on GHCR
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 2 — verify mt-node + engine images exist on GHCR"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

GH_OWNER=FlameGreat-1
GH_PAT=$(cat ~/.ghcr_pat)

# mt-node manifest
token=$(curl -sS -u "$GH_OWNER:$GH_PAT" \
  "https://ghcr.io/token?service=ghcr.io&scope=repository:flamegreat-1/etradie/mt-node:pull" \
  | jq -r .token)
mt_node_http=$(curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $token" \
  -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
  "https://ghcr.io/v2/flamegreat-1/etradie/mt-node/manifests/$PIN")
echo "mt-node manifest HTTP: $mt_node_http (expect 200)"

# engine manifest
token=$(curl -sS -u "$GH_OWNER:$GH_PAT" \
  "https://ghcr.io/token?service=ghcr.io&scope=repository:flamegreat-1/etradie/engine:pull" \
  | jq -r .token)
engine_http=$(curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $token" \
  -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
  "https://ghcr.io/v2/flamegreat-1/etradie/engine/manifests/$PIN")
echo "engine  manifest HTTP: $engine_http (expect 200)"

if [ "$mt_node_http" != "200" ] || [ "$engine_http" != "200" ]; then
  echo "FATAL: one or both images missing from GHCR. Wait for CI to finish."
  exit 1
fi

# ────────────────────────────────────────────────────────────────────
# STAGE 3 — tunnel + ArgoCD sync
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 3 — confirm K3s tunnel + force ArgoCD sync"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"
echo ""
echo "Confirm the K3s SSH tunnel is alive in your second terminal."
read -rp "Press Enter once the tunnel is alive: "

export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes

kubectl -n argocd patch application engine-staging --type merge -p '{
  "operation": {"sync": {"revision": "HEAD", "syncOptions": ["Force=true", "Replace=true"]}}
}'
kubectl -n argocd patch application mt-node-staging --type merge -p '{
  "operation": {"sync": {"revision": "HEAD", "syncOptions": ["Force=true", "Replace=true"]}}
}' 2>/dev/null || true

# ────────────────────────────────────────────────────────────────────
# STAGE 4 — engine rollout + verify the new MT_NODE_IMAGE is live
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 4 — engine rollout + verify pinned image is live in-cluster"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s

echo ""
echo "--- engine env vars ---"
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv \
  MT_NODE_IMAGE \
  MT_NODE_READINESS_TIMEOUT_SECS \
  ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS \
  ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS

echo ""
echo "Expect MT_NODE_IMAGE to contain: $PIN"
echo "Expect MT_NODE_READINESS_TIMEOUT_SECS=600"
echo "Expect ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS=1200"
echo "Expect ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS=1800"

# ────────────────────────────────────────────────────────────────────
# STAGE 5 — full cleanup (DB row + K8s + Vault)
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 5 — full cleanup"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

echo ""
echo "--- 5.1: drop hosted broker_connections rows ---"
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' RETURNING id, status;"

echo ""
echo "--- 5.2: delete all mt-node K8s resources (PVC included this time) ---"
kubectl -n etradie-system delete pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found

echo ""
echo "--- 5.3: force-remove finalizers on any stuck Terminating PVC ---"
for pvc in $(kubectl -n etradie-system get pvc \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  kubectl -n etradie-system patch pvc "$pvc" \
    -p '{"metadata":{"finalizers":null}}' --type=merge
done

echo ""
echo "--- 5.4: clean Vault tenant paths for old releases ---"
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
for old in $(kubectl -n etradie-system get events --field-selector reason=Killing 2>/dev/null \
  | grep -oE 'etradie-mt-[a-f0-9-]+' | sort -u); do
  timeout 15 kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv metadata delete -mount=etradie \
    "etradie/tenants/mt-node/$old" 2>/dev/null || true
done

echo ""
echo "--- 5.5: roll engine to invalidate per-user broker-client cache ---"
kubectl -n etradie-system rollout restart deploy/etradie-engine
kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s

echo ""
echo "--- 5.6: verify clean state ---"
kubectl -n etradie-system get pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node 2>&1
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status FROM broker_connections WHERE connection_type='hosted';"

# ────────────────────────────────────────────────────────────────────
# STAGE 6 — re-provision from dashboard
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 6 — RE-PROVISION FROM DASHBOARD NOW"
echo "=================================================================="
echo ""
echo "  Use Exness broker, primary entity, server Exness-MT5Real9,"
echo "  same login + password as before (133978149)."
echo ""
echo "  Press Enter the SECOND you click submit."
read -r
SUBMIT_TS=$(date -u +%H:%M:%S)
echo "Submit timestamp (UTC): $SUBMIT_TS" | tee submit-timestamp.txt

# ────────────────────────────────────────────────────────────────────
# STAGE 7 — race to the pod
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 7 — race to the pod"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

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
echo "REL=$REL" > release.txt
echo "POD=$POD" >> release.txt

for i in $(seq 1 60); do
  state=$(kubectl -n etradie-system get pod "$POD" \
    -o jsonpath='{.status.containerStatuses[?(@.name=="mt-node")].state}' 2>/dev/null)
  echo "[$i] mt-node state: $state"
  echo "$state" | grep -q running && break
  sleep 2
done

echo ""
echo "--- image of running mt-node container ---"
kubectl -n etradie-system get pod "$POD" \
  -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'
echo "Expect: ghcr.io/flamegreat-1/etradie/mt-node:$PIN"

# ────────────────────────────────────────────────────────────────────
# STAGE 8 — broker-bundle initContainer log
# (This is the !26 deterministic signal. Critical evidence.)
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 8 — broker-bundle initContainer log (NEW from !26)"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

echo ""
echo "--- broker-bundle init log ---"
kubectl -n etradie-system logs "$POD" -c broker-bundle 2>&1 \
  | tee broker-bundle-init.log
echo ""
echo "Expected lines:"
echo "  Downloading https://pub-5bdcacde.../broker-bundles/exness-portable.zip..."
echo "  eadee9c7...  /broker-bundle/bundle.zip: OK"
echo "  Bundle extracted successfully."

# ────────────────────────────────────────────────────────────────────
# STAGE 9 — fluxbox + tools + EWMH readiness
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 9 — tool availability + fluxbox EWMH readiness"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

sleep 10
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'which xdotool xclip xprop xwd fluxbox; echo "---"; xclip -version 2>&1 | head -1'

echo ""
echo "--- fluxbox + EWMH ---"
kubectl -n etradie-system logs "$POD" -c mt-node 2>&1 \
  | grep -iE 'fluxbox|_NET_ACTIVE_WINDOW|auto_login: start|hard-kill' | head -10

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xprop -root _NET_SUPPORTED 2>&1 | tr "," "\n" | grep -iE "_NET_ACTIVE_WINDOW" | head -3'

# ────────────────────────────────────────────────────────────────────
# STAGE 10 — broker-bundle install log (NEW from !26)
# This is the second smoking-gun signal. Must show structured lines.
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 10 — broker-bundle install log inside entrypoint.sh"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

echo ""
echo "--- broker-bundle install structured log lines ---"
kubectl -n etradie-system logs "$POD" -c mt-node 2>&1 \
  | grep -iE 'broker-bundle|Installed broker|FAILED to install|install summary' \
  | tee broker-bundle-install.log

echo ""
echo "Expected (in order):"
echo "  1. 'broker-bundle volume present at /broker-bundle; top-level listing: ...'"
echo "  2. 'broker-bundle find for servers.dat matched N file(s)' followed by paths"
echo "  3. 'Installed broker servers.dat from bundle (src=..., dst=..., dst_size=...)'"
echo "  4. 'broker-bundle install summary: servers_installed=1, ...'"
echo ""
echo "If ANY of those is missing the install path is broken and that is the bug."

# ────────────────────────────────────────────────────────────────────
# STAGE 11 — 8-minute poll loop with per-poll screenshot
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 11 — 8-minute poll loop with per-poll screenshot"
echo "=================================================================="
echo "(Take screenshots periodically as you watch this loop)"

P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"
TOTAL_POLLS=16
POLL_INTERVAL=30

for i in $(seq 1 $TOTAL_POLLS); do
  echo ""
  echo "============ poll $i / $TOTAL_POLLS  ($(date -u +%H:%M:%S)) ============"
  kubectl -n etradie-system get pod "$POD" --no-headers 2>&1 || { echo "POD GONE"; break; }

  echo ""
  echo "--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---"
  kubectl -n etradie-system logs "$POD" -c mt-node --tail=400 2>&1 \
    | grep -iE 'auto_login|MetaTrader exited|welcome modal|fluxbox|deliver|paste|type|phase3 stage|phase5|broker-bundle|Installed broker|install summary' \
    | tail -40

  echo ""
  echo "--- :5555 socket state ---"
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

  echo ""
  echo "--- accounts.dat presence ---"
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    "ls -la \"$P/config/accounts.dat\" 2>&1 | head -2"

  echo ""
  echo "--- MQL5/Logs (EA OnInit ran?) ---"
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    "ls -la \"$P/MQL5/Logs/\" 2>&1 | head -5"

  echo ""
  echo "--- servers.dat in MT_DIR (was bundle install successful?) ---"
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    "ls -la \"$P/config/servers.dat\" 2>&1; \
     [ -f \"$P/config/servers.dat\" ] && sha256sum \"$P/config/servers.dat\""

  # Capture screenshot every poll (file size tells you whether anything new rendered)
  echo ""
  echo "--- capturing framebuffer (poll $i) ---"
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    'DISPLAY=:99 xwd -root -silent > /tmp/screen.xwd 2>&1 && wc -c /tmp/screen.xwd' 2>/dev/null || true
  kubectl -n etradie-system cp etradie-system/"$POD":/tmp/screen.xwd \
    "./screen-poll-$(printf '%02d' $i).xwd" -c mt-node 2>/dev/null || true

  # Also capture window list at each poll
  kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
    'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>&1 | while read wid; do echo "WID=$wid name=$(DISPLAY=:99 xdotool getwindowname "$wid" 2>/dev/null)"; done' \
    > "windows-poll-$(printf '%02d' $i).txt" 2>&1

  sleep $POLL_INTERVAL
done

# ────────────────────────────────────────────────────────────────────
# STAGE 12 — final artifacts
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 12 — final artifacts"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

# Full mt-node container log
kubectl -n etradie-system logs "$POD" -c mt-node > driver-log-full.txt 2>&1
echo "driver-log-full.txt: $(wc -l < driver-log-full.txt) lines"

# Broker-bundle initContainer log (re-capture in case it changed)
kubectl -n etradie-system logs "$POD" -c broker-bundle > broker-bundle-init.log 2>&1
echo "broker-bundle-init.log: $(wc -l < broker-bundle-init.log) lines"

# MT5 journal (UTF-16 NUL-stripped)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log 2>/dev/null | head -1); \
   [ -n \"\$f\" ] && tr -d '\\000' < \"\$f\"" > mt5-journal.txt 2>&1
echo "mt5-journal.txt: $(wc -l < mt5-journal.txt) lines"

# EA log (MQL5/Logs)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/MQL5/Logs\"/*.log 2>/dev/null | head -1); \
   [ -n \"\$f\" ] && { echo \"=== EA log: \$f ===\"; tr -d '\\000' < \"\$f\"; } || echo '(no MQL5/Logs file)'" \
  > ea-log.txt 2>&1
echo "ea-log.txt: $(wc -l < ea-log.txt) lines"

# Final window list + screenshot
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>&1 | while read wid; do echo "WID=$wid name=$(DISPLAY=:99 xdotool getwindowname "$wid" 2>/dev/null)"; done' \
  > windows-final.txt 2>&1
cat windows-final.txt

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xwd -root -silent > /tmp/screen-final.xwd && wc -c /tmp/screen-final.xwd' 2>/dev/null || true
kubectl -n etradie-system cp etradie-system/"$POD":/tmp/screen-final.xwd ./screen-final.xwd -c mt-node 2>/dev/null

# Convert every xwd to PNG (requires imagemagick)
echo ""
echo "--- converting screenshots ---"
for f in screen-poll-*.xwd screen-final.xwd; do
  [ -s "$f" ] || continue
  png="${f%.xwd}.png"
  if convert "$f" "$png" 2>/dev/null; then
    size=$(stat -c%s "$png")
    echo "OK: $png ($size bytes)"
  else
    echo "FAIL: $f -> $png (imagemagick missing?)"
  fi
done

# ────────────────────────────────────────────────────────────────────
# STAGE 13 — verdict block
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 13 — verdict"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

echo ""
echo "--- pod state ---"
kubectl -n etradie-system get pod "$POD" 2>&1

echo ""
echo "--- accounts.dat (Phase 3 succeeded?) ---"
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/config/accounts.dat\" 2>&1" || true

echo ""
echo "--- MQL5/Logs (EA OnInit ran?) ---"
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/MQL5/Logs/\" 2>&1 | head -5" || true

echo ""
echo "--- :5555 socket (the goal) ---"
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"' || true

echo ""
echo "--- MT5 journal head + tail (broker handshake?) ---"
head -20 mt5-journal.txt 2>/dev/null
echo "..."
tail -40 mt5-journal.txt 2>/dev/null

echo ""
echo "--- DB row ---"
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, broker_id, broker_entity_id, mt5_symbol, is_active \
   FROM broker_connections WHERE connection_type='hosted';"

# ────────────────────────────────────────────────────────────────────
# STAGE 14 — structured sentinel grep
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 14 — driver sentinels (mapped to runbook §D decision tree)"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

echo ""
echo "--- !26: broker-bundle install signals (RUNBOOK D.2 / D.3 SIGNAL) ---"
grep -iE 'broker-bundle volume|broker-bundle find|broker-bundle install summary|Installed broker|FAILED to install' \
  driver-log-full.txt | head -30

echo ""
echo "--- fluxbox readiness ---"
grep -iE 'fluxbox ready' driver-log-full.txt | head -2

echo ""
echo "--- Welcome modal handling ---"
grep -iE 'welcome modal' driver-log-full.txt | head -5

echo ""
echo "--- Phase 2c (Login dialog open) ---"
grep -iE 'appeared after|all three Phase 2c|Login dialog WID=' driver-log-full.txt | head -10

echo ""
echo "--- Phase 3 strategy + per-field outcome ---"
grep -iE 'deliver |paste |type ' driver-log-full.txt | head -30

echo ""
echo "--- Phase 3 stage transitions ---"
grep -iE 'phase3 stage=' driver-log-full.txt | head -20

echo ""
echo "--- Phase 5 (chart attach) ---"
grep -iE 'phase5' driver-log-full.txt | head -30

echo ""
echo "--- Final outcome (success or failure mode) ---"
grep -iE 'LISTEN.*exit success|never bound|all three Phase 2c.*failed|hard-kill|exiting|BOTH paste and type failed|all three attempts failed' \
  driver-log-full.txt | tail -10

# ────────────────────────────────────────────────────────────────────
# STAGE 15 — files index
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 15 — diagnostic files in $DIAG_DIR"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

ls -la "$DIAG_DIR"

echo ""
echo "================================================================"
echo "Screenshots to review:"
echo "================================================================"
for f in screen-poll-*.png screen-final.png; do
  [ -f "$DIAG_DIR/$f" ] && echo "  explorer.exe $DIAG_DIR/$f"
done

echo ""
echo "================================================================"
echo "DONE. Diagnostic dir: $DIAG_DIR"
echo "================================================================"





I HAVE COPIED INTO THE NOTE.md  WHICH IS ABOUT 800 LINES THE LAST COMMANDS

MAKE SURE YOU EXAMINE EVERYTHING THOROUGHLY FROM THE BEGINNING TO THE END WITHOUT SKIP OR OR OMIT

FOR THE PNG, EVERYTHING IS BLANK EXCEPT THE screen-poll-2.png WHICH SHOWED LOGIN INPUT SO WE CANNOT ACTUALLY TELL EXACTLY WHAT HAPPENED



IT MEANS YOU SHOULD EXAMINE ALL THE ENTIRE PLACES AND FILES TRACING EVERYTHING IN THE CODEBASE THOROUGHLY  END TO END TO SEE THE EXACT CAUSE OF THE ISSUES

THEREFORE, AS A SENIOR ENGINEER YOU HAVE TO PERFORM A DEEP AND THOROUGH AUDIT ON THE ENTIRE AND WHOLE 
PIPELINE EXAMINING ALL PLACES AND FILES END TO END
 BECAUSE WE NEED TO AVOID PATCH WORK OR EASY WORK THAT WILL BREAK IN PRODUCTION

WE NEED THE RAW TRUTH OF EXACTLY HOW EVERYTHING AND THE WHOLE PIPELINE OPERATE

DO NOT STOP UNTIL YOU ARE DONE EXAMINING

AVOID ASSUMPTIONS

AVOID GUESSING

YOU MUST BE 100% CERTAIN AND SURE OF EVERY SINGLE THING TO AVOID PROBLEM

DO NOT IGNORE, SKIP OR AVOID EXAMINING ALL PLACES REQUIRED, YOU MUST EXAMINE COMPLETELY

PLEASE NOTE: DO NOT STOP UNTIL YOU ARE DONE EXAMINING ALL & COVERED EVERYTHING