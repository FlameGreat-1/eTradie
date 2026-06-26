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
# Hosted-MT staging verification — current main (overlay-normalizer +
# Config-case resolver + evidence-based chart-attach + template co-location)
#
# This script DISCOVERS the branded MT root and the resolved config dir
# at runtime (they are no longer "MetaTrader 5" + "config"); it asserts
# the behaviour shipped in the latest commits:
#   - broker-bundle overlay + normalizer (Profiles/Charts strip,
#     common.ini / accounts.dat / accounts.ini removal)
#   - MT_CONFIG_DIR case resolution (Config vs config; Deriv dual-dir)
#   - expert.tpl co-located with ZeroMQ_EA.set (+ legacy mirror)
#   - evidence-based deterministic attach vs keystroke fallback
#   - :5555 bind, EA OnInit, broker journal handshake
#   - recovery skips status='failed'
#
# Saves all artifacts to a timestamped dir.
# ─────────────────────────────────────────────────────────────────────
set -u

TS=$(date -u +%Y%m%dT%H%M%SZ)
DIAG_DIR="$HOME/hostedmt-diagnostics/${TS}"
mkdir -p "$DIAG_DIR"; cd "$DIAG_DIR"
echo "Diagnostic dir: $DIAG_DIR"

NS=etradie-system

# ── STAGE 0 — latest main + CI image pin ─────────────────────────────
echo "=== STAGE 0: confirm CI image-pin commit on top of main ==="
cd ~/eTradie
git fetch origin main && git pull --rebase origin main
git log --oneline -15
echo ""
echo "Confirm the TOP commit is the CI 'pin staging image tags' bot commit."
read -rp "Press Enter ONLY after you confirmed the CI image-pin commit is on top: "

# ── STAGE 1 — read pinned image SHA ──────────────────────────────────
echo "=== STAGE 1: pinned image SHA ==="
PIN=$(git show origin/main:helm/engine/values-staging.yaml \
  | grep -E '^[[:space:]]*tag:' | head -1 | tr -d ' "' | cut -d: -f2)
echo "Pinned SHA: $PIN"; echo "$PIN" > "$DIAG_DIR/pinned-sha.txt"
cd "$DIAG_DIR"

# ── STAGE 2 — verify images on GHCR ──────────────────────────────────
echo "=== STAGE 2: verify mt-node + engine images on GHCR ==="
GH_OWNER=FlameGreat-1
GH_PAT=$(cat ~/.ghcr_pat)
for repo in mt-node engine; do
  tok=$(curl -sS -u "$GH_OWNER:$GH_PAT" \
    "https://ghcr.io/token?service=ghcr.io&scope=repository:flamegreat-1/etradie/$repo:pull" | jq -r .token)
  code=$(curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $tok" \
    -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
    "https://ghcr.io/v2/flamegreat-1/etradie/$repo/manifests/$PIN")
  echo "$repo manifest HTTP: $code (expect 200)"
  [ "$code" = "200" ] || { echo "FATAL: $repo image $PIN missing on GHCR. Wait for CI."; exit 1; }
done

# ── STAGE 3 — tunnel + ArgoCD sync ───────────────────────────────────
echo "=== STAGE 3: K3s tunnel + ArgoCD force sync ==="
read -rp "Press Enter once the K3s SSH tunnel is alive: "
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes
kubectl -n argocd patch application engine-staging --type merge -p \
  '{"operation":{"sync":{"revision":"HEAD","syncOptions":["Force=true","Replace=true"]}}}'
kubectl -n argocd patch application mt-node-staging --type merge -p \
  '{"operation":{"sync":{"revision":"HEAD","syncOptions":["Force=true","Replace=true"]}}}' 2>/dev/null || true

# ── STAGE 4 — engine rollout + env ───────────────────────────────────
echo "=== STAGE 4: engine rollout + live env ==="
kubectl -n $NS rollout status deploy/etradie-engine --timeout=180s
kubectl -n $NS exec deploy/etradie-engine -c engine -- printenv \
  MT_NODE_IMAGE MT_NODE_READINESS_TIMEOUT_SECS \
  ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS \
  ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS 2>&1 | tee engine-env.txt
echo "Expect: MT_NODE_IMAGE contains $PIN | READINESS=600 | UNHEALTHY=1200 | FRESH=1800"

# ── STAGE 5 — full cleanup (DB + K8s + Vault) ────────────────────────
echo "=== STAGE 5: full cleanup ==="
kubectl -n $NS exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' RETURNING id, status;"
kubectl -n $NS delete pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
for pvc in $(kubectl -n $NS get pvc -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  kubectl -n $NS patch pvc "$pvc" -p '{"metadata":{"finalizers":null}}' --type=merge
done
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
for old in $(kubectl -n $NS get events --field-selector reason=Killing 2>/dev/null \
  | grep -oE 'etradie-mt-[a-f0-9-]+' | sort -u); do
  timeout 15 kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv metadata delete -mount=etradie "etradie/tenants/mt-node/$old" 2>/dev/null || true
done
kubectl -n $NS rollout restart deploy/etradie-engine
kubectl -n $NS rollout status deploy/etradie-engine --timeout=180s
kubectl -n $NS get pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node 2>&1
kubectl -n $NS exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status FROM broker_connections WHERE connection_type='hosted';"

# ── STAGE 6 — reprovision from dashboard ─────────────────────────────
echo "=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ==="
read -rp "Press Enter the SECOND you click submit: "
SUBMIT_TS=$(date -u +%H:%M:%S); echo "Submit (UTC): $SUBMIT_TS" | tee submit-timestamp.txt

# ── STAGE 7 — race to the pod ────────────────────────────────────────
echo "=== STAGE 7: race to the pod ==="
REL=""
for i in $(seq 1 30); do
  REL=$(kubectl -n $NS get statefulset -o name 2>/dev/null | grep 'etradie-mt-' | head -1 | cut -d/ -f2)
  [ -n "$REL" ] && { echo "Release: $REL"; break; }
  echo "waiting for StatefulSet... ($i)"; sleep 2
done
POD="${REL}-0"; echo "POD=$POD"; { echo "REL=$REL"; echo "POD=$POD"; } > release.txt
for i in $(seq 1 90); do
  st=$(kubectl -n $NS get pod "$POD" \
    -o jsonpath='{.status.containerStatuses[?(@.name=="mt-node")].state}' 2>/dev/null)
  echo "[$i] mt-node state: $st"; echo "$st" | grep -q running && break; sleep 2
done
kubectl -n $NS get pod "$POD" \
  -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'
echo "Expect image: ghcr.io/flamegreat-1/etradie/mt-node:$PIN"

# ── STAGE 8 — broker-bundle initContainer log ────────────────────────
echo "=== STAGE 8: broker-bundle initContainer log ==="
kubectl -n $NS logs "$POD" -c broker-bundle 2>&1 | tee broker-bundle-init.log
echo "Expect: 'Downloading ...exness-portable.zip', 'eadee9c7... OK', 'Bundle extracted successfully.'"

# ── STAGE 8b — DISCOVER the branded MT root + resolved config dir ─────
# Everything downstream uses these discovered values, NOT hardcoded paths.
echo "=== STAGE 8b: discover MT_DIR (branded root) + MT_CONFIG_DIR ==="
sleep 8
MT_DIR=$(kubectl -n $NS exec "$POD" -c mt-node -- sh -c '
  base="/home/mt/.wine/prefix/drive_c/Program Files"
  base32="/home/mt/.wine/prefix/drive_c/Program Files (x86)"
  d=$(find "$base" "$base32" -maxdepth 2 -type f -iname "terminal64.exe" -o -iname "terminal.exe" 2>/dev/null | head -1)
  [ -n "$d" ] && dirname "$d"
' 2>/dev/null)
echo "Discovered MT_DIR: '$MT_DIR'"
echo "$MT_DIR" > mt-dir.txt
[ -n "$MT_DIR" ] || { echo "FATAL: could not discover branded MT root (terminal*.exe not found)."; }

MT_CONFIG_DIR=$(kubectl -n $NS exec "$POD" -c mt-node -- sh -c "
  for c in \"$MT_DIR/Config\" \"$MT_DIR/config\"; do [ -d \"\$c\" ] && { echo \"\$c\"; break; }; done
" 2>/dev/null)
echo "Discovered MT_CONFIG_DIR: '$MT_CONFIG_DIR'"
echo "$MT_CONFIG_DIR" > mt-config-dir.txt

# ── STAGE 9 — tools + fluxbox EWMH readiness ─────────────────────────
echo "=== STAGE 9: tools + fluxbox EWMH ==="
kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
  'which xdotool xclip xprop xwd fluxbox; echo "---"; xclip -version 2>&1 | head -1' 2>&1
kubectl -n $NS logs "$POD" -c mt-node 2>&1 \
  | grep -iE 'fluxbox|_NET_ACTIVE_WINDOW|auto_login: start|hard-kill' | head -10
kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xprop -root _NET_SUPPORTED 2>&1 | tr "," "\n" | grep -i _NET_ACTIVE_WINDOW | head -3' 2>&1

# ── STAGE 10 — overlay-normalizer evidence (NEW behaviour) ───────────
echo "=== STAGE 10: overlay normalizer + config-resolve log lines ==="
kubectl -n $NS logs "$POD" -c mt-node 2>&1 \
  | grep -iE 'overlay-normalize|canonical config dir|broker-bundle overlay|config dir resolved' \
  | tee overlay-normalize.log
echo ""
echo "Expect lines like:"
echo "  overlay-normalize(mt5): stripping baked Profiles/Charts workspace"
echo "  overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace"
echo "  overlay-normalize(mt5): removing baked common.ini ..."
echo "  overlay-normalize(mt5): removing baked accounts.dat ..."
echo "  overlay-normalize: canonical config dir resolved to '<MT_DIR>/Config'"

# ── STAGE 10b — assert normalizer RESULT on disk ─────────────────────
echo "=== STAGE 10b: assert baked state was actually neutralized ==="
kubectl -n $NS exec "$POD" -c mt-node -- sh -c "
  echo '--- Profiles/Charts (MUST be absent or empty) ---'
  ls -la \"$MT_DIR/Profiles/Charts\" 2>&1 | head -3
  ls -la \"$MT_DIR/MQL5/Profiles/Charts\" 2>&1 | head -3
  echo '--- common.ini (MUST be absent until MT5 recreates it) ---'
  ls -la \"$MT_CONFIG_DIR/common.ini\" 2>&1
  echo '--- stray lowercase config dir (MUST be absent on Deriv after de-dup) ---'
  ls -la \"$MT_DIR/config\" 2>&1 | head -2
  echo '--- expert.tpl co-located with the .set (BOTH MUST exist) ---'
  ls -la \"$MT_DIR/MQL5/Profiles/Templates/expert.tpl\" \"$MT_DIR/MQL5/Profiles/Templates/ZeroMQ_EA.set\" 2>&1
  echo '--- expert.tpl legacy mirror ---'
  ls -la \"$MT_DIR/Profiles/Templates/expert.tpl\" 2>&1
  echo '--- our startup.ini in the resolved config dir ---'
  ls -la \"$MT_CONFIG_DIR/startup.ini\" 2>&1
  echo '--- servers.dat present (broker server list) ---'
  ls -la \"$MT_CONFIG_DIR/servers.dat\" 2>&1
" 2>&1 | tee on-disk-asserts.txt

# ── STAGE 11 — 8-minute poll loop ────────────────────────────────────
echo "=== STAGE 11: poll loop ==="
TOTAL_POLLS=16; POLL_INTERVAL=30
for i in $(seq 1 $TOTAL_POLLS); do
  echo ""; echo "===== poll $i/$TOTAL_POLLS  $(date -u +%H:%M:%S) ====="
  kubectl -n $NS get pod "$POD" --no-headers 2>&1 || { echo "POD GONE"; break; }

  echo "--- driver log (auto_login / deterministic / phase5 / overlay) ---"
  kubectl -n $NS logs "$POD" -c mt-node --tail=400 2>&1 \
    | grep -iE 'auto_login|deterministic attach|chart\+EA|phase5|deliver|paste|type|phase3 stage|login gate|MetaTrader exited|overlay-normalize' \
    | tail -40

  echo "--- :5555 LISTEN state (0A) ---"
  kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
    'awk "NR>1 && \$4==\"0A\" && (\$2 ~ /:15B3\$/ || \$3 ~ /:15B3\$/){print}" /proc/net/tcp' 2>&1

  echo "--- EA Experts log (chart+EA attach + bind banner) ---"
  kubectl -n $NS exec "$POD" -c mt-node -- sh -c "
    f=\$(ls -t \"$MT_DIR/MQL5/Logs\"/*.log 2>/dev/null | head -1)
    [ -n \"\$f\" ] && tr -d '\000' < \"\$f\" | grep -aE 'loaded successfully|ZeroMQ Bridge Started|Failed to bind|Duplicate EA' | tail -6 || echo '(no MQL5/Logs yet)'
  " 2>&1

  echo "--- accounts.dat (recreated after first login?) ---"
  kubectl -n $NS exec "$POD" -c mt-node -- sh -c "ls -la \"$MT_CONFIG_DIR/accounts.dat\" 2>&1 | head -2" 2>&1

  kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
    'DISPLAY=:99 xwd -root -silent > /tmp/screen.xwd 2>&1 && wc -c /tmp/screen.xwd' 2>/dev/null || true
  kubectl -n $NS cp "$NS/$POD":/tmp/screen.xwd "./screen-poll-$(printf '%02d' $i).xwd" -c mt-node 2>/dev/null || true
  kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
    'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>/dev/null | while read w; do echo "WID=$w name=$(DISPLAY=:99 xdotool getwindowname "$w" 2>/dev/null)"; done' \
    > "windows-poll-$(printf '%02d' $i).txt" 2>&1
  sleep $POLL_INTERVAL
done

# ── STAGE 12 — final artifacts ───────────────────────────────────────
echo "=== STAGE 12: final artifacts ==="
kubectl -n $NS logs "$POD" -c mt-node > driver-log-full.txt 2>&1
kubectl -n $NS logs "$POD" -c broker-bundle > broker-bundle-init.log 2>&1
kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$MT_DIR/logs\"/*.log 2>/dev/null | head -1); [ -n \"\$f\" ] && tr -d '\000' < \"\$f\"" > mt5-journal.txt 2>&1
kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$MT_DIR/MQL5/Logs\"/*.log 2>/dev/null | head -1); [ -n \"\$f\" ] && { echo \"=== \$f ===\"; tr -d '\000' < \"\$f\"; } || echo '(no MQL5/Logs file)'" > ea-log.txt 2>&1
kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>/dev/null | while read w; do echo "WID=$w name=$(DISPLAY=:99 xdotool getwindowname "$w" 2>/dev/null)"; done' > windows-final.txt 2>&1
kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xwd -root -silent > /tmp/screen-final.xwd && wc -c /tmp/screen-final.xwd' 2>/dev/null || true
kubectl -n $NS cp "$NS/$POD":/tmp/screen-final.xwd ./screen-final.xwd -c mt-node 2>/dev/null
for f in screen-poll-*.xwd screen-final.xwd; do
  [ -s "$f" ] || continue; convert "$f" "${f%.xwd}.png" 2>/dev/null \
    && echo "OK: ${f%.xwd}.png" || echo "FAIL convert $f (imagemagick?)"
done

# ── STAGE 13 — verdict ───────────────────────────────────────────────
echo "=== STAGE 13: verdict ==="
kubectl -n $NS get pod "$POD" 2>&1
echo "--- :5555 LISTEN (the goal) ---"
kubectl -n $NS exec "$POD" -c mt-node -- sh -c \
  'awk "NR>1 && \$4==\"0A\" && (\$2 ~ /:15B3\$/ || \$3 ~ /:15B3\$/){print}" /proc/net/tcp' 2>&1
echo "--- journal head/tail (broker handshake) ---"
head -20 mt5-journal.txt 2>/dev/null; echo "..."; tail -40 mt5-journal.txt 2>/dev/null
echo "--- DB row ---"
kubectl -n $NS exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, broker_id, broker_entity_id, mt5_symbol, is_active \
   FROM broker_connections WHERE connection_type='hosted';"

# ── STAGE 14 — sentinel grep mapped to the new code ──────────────────
echo "=== STAGE 14: driver sentinels ==="
echo "--- overlay normalizer ---"
grep -iE 'overlay-normalize|canonical config dir' driver-log-full.txt | head -20
echo "--- deterministic attach decision (evidence-based) ---"
grep -iE 'deterministic attach' driver-log-full.txt | head -20
echo "--- chart+EA presence gating ---"
grep -iE 'chart\+EA|loaded successfully|Bridge Started|Failed to bind|Duplicate EA' driver-log-full.txt ea-log.txt | head -20
echo "--- phase5 fallback (should be RARE / skipped) ---"
grep -iE 'phase5' driver-log-full.txt | head -20
echo "--- final outcome ---"
grep -iE 'LISTEN.*exit success|never bound|login gate|hard-kill|all three attempts failed' driver-log-full.txt | tail -10

# ── STAGE 15 — files index ───────────────────────────────────────────
echo "=== STAGE 15: artifacts in $DIAG_DIR ==="
ls -la "$DIAG_DIR"
echo "DONE. Diagnostic dir: $DIAG_DIR"





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