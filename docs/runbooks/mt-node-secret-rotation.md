# mt-node secret rotation runbook

Operator-facing procedures for rotating every credential the mt-node
stack handles. These flows are designed to be runnable during market
hours with **zero user-visible downtime** when followed in the order
documented below.

| Rotation flow | Frequency | Downtime | Section |
|---|---|---|---|
| (a) Per-tenant ZMQ auth token (one user) | 90d routine / on compromise | zero | [Section A](#a-per-tenant-zmq-auth-token-rotation) |
| (b) Platform encryption key (`MT_NODE_CREDENTIAL_ENCRYPTION_KEY`) | annual / on compromise | zero | [Section B](#b-platform-encryption-key-rotation) |
| (c) User's MT5 broker password | user-driven | zero | [Section C](#c-broker-password-rotation) |
| (d) `BROKER_ENCRYPTION_KEY` (engine Fernet key for DB column ciphertext) | annual / on compromise | brief (single rolling restart) | [Section D](#d-broker_encryption_key-rotation) |

## Pre-flight (all flows)

Before any rotation:

```bash
# 1. Confirm the engine is healthy.
kubectl -n etradie-system rollout status deploy/engine --timeout=30s

# 2. Confirm HostedRecoveryService is not currently sweeping. If a
#    sweep is in flight, wait for it to finish (last_run_timestamp
#    should be < sweep_interval_secs old).
kubectl -n etradie-system exec deploy/engine -c engine -- \
  curl -sf http://localhost:8000/metrics \
  | grep -E '(etradie_hosted_recovery_last_run_timestamp_seconds|etradie_hosted_recovery_runs_total)'

# 3. Snapshot the broker_connections row(s) you are about to touch
#    so a rollback is one-line if needed.
kubectl -n etradie-system exec deploy/postgres -c postgres -- \
  psql -U etradie -d etradie -c \
  "SELECT id, user_id, connection_type, mt5_server, mt5_login, status, updated_at \
   FROM broker_connections WHERE id = '<CONNECTION_ID>'\\gx"
```

---

## A. Per-tenant ZMQ auth token rotation

**When**: 90-day rotation policy; suspected token compromise; user
reports a security incident on their account.

**What happens**: the engine's `HostedProvisioner.provision_account()`
generates a fresh `secrets.token_hex(32)` token, writes a new K8s
Secret (`<release>-creds`), and the StatefulSet rolling-updates the
Pod (because the chart's `checksum/sealed-secret-name` annotation
is recomputed). The ZmqClient picks up the new token from
`broker_connections.ea_auth_token` on the next factory construction.

**Procedure**:

```bash
# 1. Acquire an admin service-token JWT. The exact mechanism is
#    cluster-specific; in the default deployment it comes from the
#    gateway's /internal/admin/issue-token endpoint.
ADMIN_JWT=$(kubectl -n etradie-system exec deploy/gateway -c gateway -- \
  /usr/local/bin/gateway issue-service-token --scope=admin --ttl=15m)

# 2. Run the rotation helper. The script deletes the connection,
#    re-creates it with the SAME MT credentials, and asserts the new
#    connection lands in status='connected' within readiness-gate
#    timeout (default 5 min).
python3 scripts/rotate-mt-node-token.py \
  --connection-id=<CONNECTION_ID> \
  --engine-url=https://engine.etradie-system.svc.cluster.local:8000 \
  --jwt="${ADMIN_JWT}"

# 3. Verify the new token is in place.
kubectl -n etradie-system get secret etradie-mt-<id[:12]>-creds \
  -o jsonpath='{.data.MT_ZMQ_AUTH_TOKEN}' | base64 -d | head -c 12
# (compare to what you snapshotted in pre-flight)
```

**Verification** (within 60s of rotation):

- The Pod's `mt_node_ea_authenticated` metric returns to 1.
- The watchdog `mt_node_watchdog_socket_resets_total` increments
  exactly once (the new token resets the watchdog's REQ socket
  on first probe).
- `broker_connections.status` transitions to `connected`.

**Rollback**: if the new connection does not reach
`status='connected'` within 5 minutes, restore the snapshotted row
state with a direct `UPDATE broker_connections SET ea_auth_token =
'<old-encrypted>' WHERE id = '...'` and call the engine's
`/api/broker/connections/<id>/test` endpoint to rebuild the
client.

---

## B. Platform encryption key rotation

**When**: annual rotation policy; suspected Vault compromise; HSM
key-policy change.

**What's at stake**: `MT_NODE_CREDENTIAL_ENCRYPTION_KEY` is used by
`HostedProvisioner._seal()` (AES-GCM) to write the `ETRADIE_SEAL`
blob inside every per-tenant K8s Secret. The blob is
**defence-in-depth** only - the per-tenant Pod reads the PLAIN
`MT_LOGIN` / `MT_PASSWORD` / `MT_ZMQ_AUTH_TOKEN` keys, not the seal
blob. Rotating the platform key therefore does NOT invalidate any
existing tenant; it just leaves stale seal blobs that the
follow-up sweep replaces.

**Procedure**:

```bash
# 1. Generate the new key.
NEW_KEY=$(openssl rand -hex 32)

# 2. Patch Vault. The engine ExternalSecret refreshInterval is 1h,
#    so we trigger a manual refresh instead of waiting.
vault kv patch etradie/services/mt-node/production \
  mt_node_credential_encryption_key="${NEW_KEY}"
kubectl -n etradie-system annotate externalsecret etradie-engine \
  force-sync="$(date +%s)" --overwrite
kubectl -n etradie-system rollout restart deploy/engine
kubectl -n etradie-system rollout status deploy/engine --timeout=5m

# 3. Force HostedRecoveryService to re-seal every connection. Two
#    ways:
#    (a) Wait for the next periodic sweep (default 60s) - it only
#        reprovisions UNHEALTHY connections, so this does NOT touch
#        healthy ones. The old seal blobs persist on healthy Pods.
#    (b) For a complete re-seal, trigger an admin rotation that
#        re-provisions every active connection:
kubectl -n etradie-system exec deploy/engine -c engine -- \
  curl -X POST -H "Authorization: Bearer ${ADMIN_JWT}" \
  http://localhost:8000/internal/admin/hosted/reseal-all
```

**Verification**:

- Every per-tenant Secret's `ETRADIE_SEAL` value differs from the
  pre-rotation snapshot.
- `etradie_hosted_recovery_reprovisions_total{reason="reseal"}`
  matches the count of active hosted connections.
- No tenant ever experiences a `mt_node_ea_authenticated=0` window.

**Rollback**: keep the OLD key in Vault under
`mt_node_credential_encryption_key_previous` for 7 days post
rotation. If the new key turns out to be unusable, restore via
`vault kv patch ... mt_node_credential_encryption_key=<old>` +
restart.

---

## C. Broker password rotation

**When**: user changes their MT5 broker password in the broker's UI.

**Procedure** (user-initiated; this section is for operator
awareness):

1. User opens dashboard -> Broker Connections -> their hosted
   connection -> Update Connection -> new password.
2. The engine encrypts the new password under the current
   `BROKER_ENCRYPTION_KEY` (Fernet) and overwrites
   `broker_connections.mt5_password_encrypted`.
3. `HostedProvisioner.provision_account()` runs as part of the
   update flow: it overwrites the per-tenant K8s Secret with the
   new password (plain base64 inside `MT_PASSWORD`) and the
   StatefulSet's checksum/sealed-secret-name annotation forces a
   Pod restart.
4. The Pod boots; `entrypoint.sh` reads the new password from
   envFrom; MT5 auto-logins with it.

Expected user-visible downtime: ~30-60 seconds (the Wine prefix
PVC re-attaches; MT5 first-boot is skipped because the broker's
"trusted device" registration persists in `~/.wine`).

---

## D. BROKER_ENCRYPTION_KEY rotation

**When**: annual rotation policy; suspected Vault compromise.

**What's at stake**: every `mt5_password_encrypted` ciphertext in
the `broker_connections` Postgres table was encrypted under the
OLD key (Fernet, derived from the env var via SHA256 in
`broker_connection_repository._derive_encryption_key`). A naive
key swap renders every ciphertext undecryptable.

**Procedure** (dual-key window):

```bash
# 1. Generate the new key.
NEW_KEY=$(openssl rand -hex 32)

# 2. Patch Vault with BOTH keys, alias-ing the new one as the
#    PRIMARY and keeping the old one accessible.
vault kv patch etradie/services/engine/production \
  broker_encryption_key="${NEW_KEY}" \
  broker_encryption_key_previous="<OLD_KEY>"

# 3. Deploy a dual-key engine build (this requires a code change to
#    broker_connection_repository._derive_encryption_key to try the
#    new key first, then the previous one on failure). Until that
#    code lands, rotation requires brief downtime + a re-encrypt
#    migration:

# 3a. Stop the engine.
kubectl -n etradie-system scale deploy/engine --replicas=0

# 3b. Re-encrypt every row in broker_connections using a one-shot
#     migration script. The script reads each row, decrypts under
#     the OLD key, encrypts under the NEW key, and writes back.
python3 scripts/reencrypt-broker-connections.py \
  --old-key="$(vault kv get -field=broker_encryption_key_previous etradie/services/engine/production)" \
  --new-key="${NEW_KEY}"

# 3c. Restart the engine.
kubectl -n etradie-system scale deploy/engine --replicas=2
kubectl -n etradie-system rollout status deploy/engine --timeout=5m

# 4. Drop the old key from Vault after 7 days.
vault kv patch etradie/services/engine/production \
  broker_encryption_key_previous=""
```

**Note**: the `scripts/reencrypt-broker-connections.py` script and
the `_derive_encryption_key` dual-key logic are tracked as a
follow-up MR; this runbook is the design pre-doc so the operator
procedure is reviewable BEFORE the code lands.

**Verification**:

- Every `mt5_password_encrypted` row decrypts successfully under
  the new key (validated by the migration script's exit code).
- The engine's startup log shows no `decrypt_credential` failures.
- A spot-check of one hosted connection: the
  `provision_account()` call in `HostedRecoveryService.run_once_at_startup()`
  succeeds for the spot-checked connection.

---

## Cross-rotation safety net

- All four flows leave `BROKER_ENCRYPTION_KEY` and
  `MT_NODE_CREDENTIAL_ENCRYPTION_KEY` ORTHOGONAL. A bug in one
  rotation cannot corrupt the other.
- The `HostedRecoveryService` is the safety net: a permanently
  broken connection (e.g. wrong key after a failed rotation) is
  surfaced via the `HostedRecoveryReprovisionsHigh` alert within
  2 hours of the rotation. Operators on call see the alert AND
  the structured logs identifying the affected `connection_id`.
