
Both let you `kubectl` from your workstation against the K3s cluster on the VPS.

**`ssh-add ~/.ssh/id_ed25519`** — unlocks your SSH key once per WSL boot, so commands like `ssh` and `scp` don't prompt for the passphrase every time.

**`ssh -N -L 6443:127.0.0.1:6443 etradie@...`** — opens the encrypted tunnel that lets `kubectl get pods`, `kubectl apply`, `helm install`, `argocd app sync` (every Phase 3+ command on the workstation) reach the K3s API. Without this tunnel, kubectl hangs because the VPS firewall blocks the API publicly.

**Daily use pattern after a WSL reboot:**

```bash
ssh-add ~/.ssh/id_ed25519                                  # passphrase once
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173       # in a dedicated terminal, leave open
# then in other terminals, kubectl/helm/argocd just work
kubectl get nodes
```

That's it. Phase 3 onward needs both running.

WE ARE WORKING ON THE DEPLOYMENT FOR THE STAGING OF THE EXOPER. THE /docs/runbooks/README.md CONTAINS THE FULL DEPLOYMENT PHASES STEP BY STEP.

AND WE HAVE DONE PHASE 0, 1, 2, 3, 4, 5, 6 AND 7 AS YOU CAN SEE IN THE /docs/runbooks/README.md AND THE /docs/runbooks/PROGRESS.md

SO YOU EXAMINE BOTH FILES THOROUGHLY FROM THE BEGINNING TO THE END.

 EXAMINE IT  THOROUGHLY FROM  THE BEGINNING TO THE END BECAUSE YOU NEED TO UNDERSTAND AND KNOW HOW TO PICK UP FROM WHERE WE STOPPED

 SO WE ARE GOING TO CONTINUE WITH PHASE 8 THIS IS WHAT YOU SAID LAST IN THE PREVIOUS SESSION:


 Everything landed cleanly. Status:

- **All 3 commits** on both remotes at `6fcb0d82` ✓ — sync rhythm working.
- **ClusterSecretStore patched**: `etradie Valid` — ESO now reads from the canonical mount, aligning with what terraform wrote.

§8.1 is fully closed. **Phase 8.1 = ✅ DONE on the live cluster.** Ready for §8.2.

#### Verify shell state before §8.2 (don't trust it)

You changed terminals during the previous turn. Let me check what survived:

```bash
cd ~/eTradie
pwd
echo "KUBECONFIG=$KUBECONFIG"
echo "ROOT_TOKEN length: ${#ROOT_TOKEN} chars (expect 28)"
kubectl get nodes
```

Paste the four lines. If `ROOT_TOKEN` is 0 chars, re-export with the recovery block:

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
export ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
echo "ROOT_TOKEN length: ${#ROOT_TOKEN} chars"
```

#### §8.2 — Generate the 9 shared secrets ONCE + define helper functions

Once shell state is green, paste this block. It does five things in one go:

1. Generates 9 random secrets (passwords, JWT, KEK, etc.).
2. Computes 4 DSN/URL strings from those secrets.
3. Defines the three Vault helper functions (`vkv`, `vkv_get`, `vkv_file`).
4. Writes `~/etradie-staging-creds.txt` (mode 0600) as the workstation recovery copy.
5. Prints length-only sanity checks (no secret values revealed).

```bash
cd ~/eTradie

# === §8.2 — Generate shared secrets ONCE ===

DB_PASS=$(openssl rand -hex 32)
REDIS_PASS=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 64)            # 128 hex chars
BROKER_KEY=$(openssl rand -hex 32)            # Tier 3 KEK, engine-only
CHROMA_TOKEN=$(openssl rand -hex 32)
ADMIN_PASS=$(openssl rand -hex 24)            # 48 hex chars; rotate after first login
ENGINE_SHARED=$(openssl rand -hex 32)         # X-Internal-Auth: callers → engine
BILLING_SHARED=$(openssl rand -hex 32)        # X-Internal-Auth: gateway → billing
MT_DEFAULT_ZMQ=$(openssl rand -hex 32)

# DSN construction (sslmode=require — engine + billing fail-closed otherwise).
DB_URL_GO="postgres://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=require"
DB_URL_PY="postgresql+asyncpg://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=require"
REDIS0="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/0"
REDIS1="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/1"

echo "=== §8.2 length sanity checks (no values echoed) ==="
echo "DB_PASS=${#DB_PASS} (expect 64) $( [ ${#DB_PASS} -eq 64 ] && echo OK || echo FAIL )"
echo "REDIS_PASS=${#REDIS_PASS} (expect 64) $( [ ${#REDIS_PASS} -eq 64 ] && echo OK || echo FAIL )"
echo "JWT_SECRET=${#JWT_SECRET} (expect 128) $( [ ${#JWT_SECRET} -eq 128 ] && echo OK || echo FAIL )"
echo "BROKER_KEY=${#BROKER_KEY} (expect 64) $( [ ${#BROKER_KEY} -eq 64 ] && echo OK || echo FAIL )"
echo "CHROMA_TOKEN=${#CHROMA_TOKEN} (expect 64) $( [ ${#CHROMA_TOKEN} -eq 64 ] && echo OK || echo FAIL )"
echo "ADMIN_PASS=${#ADMIN_PASS} (expect 48) $( [ ${#ADMIN_PASS} -eq 48 ] && echo OK || echo FAIL )"
echo "ENGINE_SHARED=${#ENGINE_SHARED} (expect 64) $( [ ${#ENGINE_SHARED} -eq 64 ] && echo OK || echo FAIL )"
echo "BILLING_SHARED=${#BILLING_SHARED} (expect 64) $( [ ${#BILLING_SHARED} -eq 64 ] && echo OK || echo FAIL )"
echo "MT_DEFAULT_ZMQ=${#MT_DEFAULT_ZMQ} (expect 64) $( [ ${#MT_DEFAULT_ZMQ} -eq 64 ] && echo OK || echo FAIL )"

# === §8.3 — Persist to ~/etradie-staging-creds.txt BEFORE any vault writes ===

umask 077
cat > ~/etradie-staging-creds.txt <<EOF
# eTradie §8.2 generated secrets — staging — $(date -u +%FT%TZ)
# mode 0600. Workstation safety net until Phase 15 Vault Raft snapshots.
# Vault remains canonical; this file is the recovery reference.
DB_PASS=${DB_PASS}
REDIS_PASS=${REDIS_PASS}
JWT_SECRET=${JWT_SECRET}
ADMIN_PASS=${ADMIN_PASS}
BROKER_KEY=${BROKER_KEY}
CHROMA_TOKEN=${CHROMA_TOKEN}
ENGINE_SHARED=${ENGINE_SHARED}
BILLING_SHARED=${BILLING_SHARED}
MT_DEFAULT_ZMQ=${MT_DEFAULT_ZMQ}
EOF
chmod 600 ~/etradie-staging-creds.txt
ls -la ~/etradie-staging-creds.txt
echo "OK §8.3 creds file written, mode 0600"

# === Define helpers for §8.4–§8.11 (these write via kubectl exec, no port-forward needed) ===

vkv () {
  kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" vault kv put "$@"
}
vkv_get () {
  kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" vault kv get "$@"
}
vkv_file () {
  local path="$1"; shift
  local -a kv=()
  while [ "$#" -gt 0 ]; do
    local k="${1%%=*}"; local v="${1#*=}"
    if [ "${v#@}" != "$v" ]; then
      v="$(cat "${v#@}")"
    fi
    kv+=("$k=$v"); shift
  done
  kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv put "$path" "${kv[@]}"
}

# Confirm the helpers are defined.
type vkv vkv_get vkv_file 2>&1 | head -15

echo ""
echo "=== §8.2 + §8.3 complete; helpers defined; ready for §8.4 ==="
```

#### What to expect

- 9 length sanity lines, all ending `OK`.
- `ls -la ~/etradie-staging-creds.txt` showing mode `-rw-------` and ~700 bytes.
- `OK §8.3 creds file written, mode 0600`.
- `type vkv` etc. prints `vkv is a function` followed by the function body (3 short multi-line blocks).
- Final line: `=== §8.2 + §8.3 complete; helpers defined; ready for §8.4 ===`.

#### Critical reminder

**Do NOT close this terminal between now and §8.11.** The 13 generated variables (`DB_PASS` through `MT_DEFAULT_ZMQ`, plus the 4 URL strings) are session-only. The helper functions are session-only. Losing the shell means re-sourcing from `~/etradie-staging-creds.txt` AND re-defining the helpers — a real chore.

Paste back:
1. Shell state verification (pwd + KUBECONFIG + ROOT_TOKEN length + kubectl get nodes).
2. The 9 length sanity lines.
3. The `ls -la` for the creds file.
4. The helpers `type` output.
5. The final "ready for §8.4" line.

If all 9 length checks print OK and the helpers are defined, we go straight to §8.4 (data-layer paths) in the next message.


§8.2 + §8.3 + helpers all complete cleanly. Status:

- **All 9 secrets generated** with correct lengths ✓
- **Creds file written**: 950 bytes, mode `-rw-------` ✓
- **3 helper functions defined** (vkv, vkv_get, vkv_file) ✓

Shell state is good. Ready for §8.4.

#### §8.4 — Data-layer paths (postgres + redis + chromadb)

Three Vault writes. These come FIRST because the data-layer StatefulSets are wave -2 in Phase 12 and block in `Init:0/N` if their secrets don't exist.

```bash
cd ~/eTradie

# === §8.4 — Data-layer Vault paths ===

echo "=== §8.4 — writing data-layer paths ==="

# 8.4.1 — Postgres: 3 properties.
vkv etradie/data-layer/postgres/staging \
  postgres_user=etradie \
  postgres_db=etradie \
  postgres_password="${DB_PASS}"

# 8.4.2 — Redis: 1 property.
vkv etradie/data-layer/redis/staging \
  redis_password="${REDIS_PASS}"

# 8.4.3 — ChromaDB: 1 property. SINGLE source of truth — both the
# chromadb StatefulSet AND the engine pod read this exact path.
vkv etradie/data-layer/chromadb/staging \
  auth_token="${CHROMA_TOKEN}"

echo ""
echo "=== §8.4 read-back verification (length-only, no values echoed) ==="

# Postgres read-back — check 3 properties all present.
pg_user=$(vkv_get -field=postgres_user etradie/data-layer/postgres/staging 2>/dev/null)
pg_db=$(vkv_get -field=postgres_db etradie/data-layer/postgres/staging 2>/dev/null)
pg_pass_len=$(vkv_get -field=postgres_password etradie/data-layer/postgres/staging 2>/dev/null | wc -c)
echo "postgres/staging: user=${pg_user} db=${pg_db} password_length=${pg_pass_len} (expect 64)"

# Redis read-back.
redis_pass_len=$(vkv_get -field=redis_password etradie/data-layer/redis/staging 2>/dev/null | wc -c)
echo "redis/staging: password_length=${redis_pass_len} (expect 64)"

# ChromaDB read-back.
chroma_len=$(vkv_get -field=auth_token etradie/data-layer/chromadb/staging 2>/dev/null | wc -c)
echo "chromadb/staging: auth_token_length=${chroma_len} (expect 64)"

# Hash-compare DB_PASS in shell against what Vault returned (no value leak).
shell_hash=$(printf '%s' "${DB_PASS}" | sha256sum | cut -d' ' -f1)
vault_hash=$(vkv_get -field=postgres_password etradie/data-layer/postgres/staging 2>/dev/null | sha256sum | cut -d' ' -f1)
echo ""
echo "DB_PASS equality check:"
echo "  shell hash:  ${shell_hash}"
echo "  vault hash:  ${vault_hash}"
[ "$shell_hash" = "$vault_hash" ] && echo "  OK MATCH (Vault holds exactly what was generated)" || echo "  FAIL MISMATCH"
```

#### What to expect

- Three `Success! Data written to: etradie/data/...` lines (one per vkv call). ← key indicator the write succeeded.
- `postgres/staging: user=etradie db=etradie password_length=64 (expect 64)` — note: `wc -c` includes a trailing newline, so the actual visible result might be 65. Don't worry if it's 65 — the hash-compare below is the authoritative check.

Actually, on second thought, `wc -c` returning 65 instead of 64 is the right behavior because `vault kv get -field=foo` appends a newline. Let me adjust expectations:

- Length lines will probably show 65 (the value's 64 hex chars + trailing `\n` from the CLI). That's fine.
- The hash-compare line at the bottom is the load-bearing one. It uses `sha256sum` which is exact byte-for-byte comparison.

#### Paste back

1. The three `Success! Data written to: ...` lines.
2. The 3 read-back length lines (postgres/redis/chromadb).
3. The DB_PASS equality block — **especially the "MATCH" or "MISMATCH" line**.

If any `Success!` line is missing OR the equality says MISMATCH, stop and paste the full output. Otherwise we proceed straight to §8.5 (Linkerd mesh CA).



Confirmed — the chart values pin `vaultPath: etradie/data-layer/postgres/staging` (NO double `etradie/` prefix). The ExternalSecret then passes this path to ESO, which via the ClusterSecretStore (mount=`etradie`) translates it to the API call `etradie/data/etradie/data-layer/postgres/staging`.

Wait — ESO interprets the `vaultPath` as the **key** within the mount, so:

- ClusterSecretStore: `path: etradie` (mount root)
- ExternalSecret `remoteRef.key`: `etradie/data-layer/postgres/staging`
- API call ESO makes: `etradie/data/etradie/data-layer/postgres/staging` (mount/data/key)

So ESO is going to look at `etradie/data/etradie/data-layer/postgres/staging` — which is the path TERRAFORM created and where the placeholder lives. But my §8.4 vkv wrote to `etradie/data/data-layer/postgres/staging` (without the `etradie/` prefix in the key).

**So §8.4 wrote to the WRONG paths.** ESO would read the empty terraform placeholders, not my §8.4 writes.

#### Verify the mistake before fixing

```bash
# What §8.4 actually wrote (no etradie/ prefix in the path arg):
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie data-layer/postgres/staging 2>&1 | head -20

# What the chart ExternalSecret will read (with etradie/ prefix in the key,
# which is what terraform created):
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie etradie/data-layer/postgres/staging 2>&1 | head -20
```

The first should show our real secret (postgres_user=etradie, postgres_password=<hash>...). The second should show the terraform `bootstrap: placeholder` text.

Paste back both outputs. We need to confirm before I send the fix.

If confirmed, the fix is straightforward: re-run §8.4 with the correct path prefix (`etradie/data-layer/...` instead of `data-layer/...`). Vault KV-v2 will create a version 2 of each path; ESO reads only the latest version, so the existing placeholders just get superseded.

Don't run §8.5 yet. We resolve this path divergence on §8.4 first.

#### Side note — why this happened

My §8.4 helper command was:

```bash
vkv etradie/data-layer/postgres/staging
```

That looks correct (matches the chart's `vaultPath`). But it omits the `etradie/` PREFIX that terraform's resource naming convention includes (`name = "etradie/data-layer/postgres/staging"` in main.tf → API path `etradie/data/etradie/data-layer/postgres/staging`).

The fix is consistent: every `vkv` and `vkv_file` call in §8.4–§8.11 should use **`etradie/...`** as the path argument (matching terraform's resource names), NOT just the unprefixed form.

I'll send the corrected §8.4 + the rest of Phase 8 after you confirm the path divergence is real.








rse@Softverse:~/eTradie/infrastructure/cluster/vault-paths$
softverse@Softverse:~/eTradie/infrastructure/cluster/vault-paths$ cd ~/eTradie/infrastructure/cluster/vault-paths

# Verify all five variables still set in this shell.
echo "VAULT_TOKEN length: ${#VAULT_TOKEN}, VAULT_ADDR=$VAULT_ADDR"
echo "K8S_HOST=$K8S_HOST"
echo "K8S_CA_CERT length: ${#K8S_CA_CERT}"
echo "K8S_REVIEWER_JWT length: ${#K8S_REVIEWER_JWT}"

# Apply.
terraform apply -auto-approve \
  -var environment=staging \
  -var vault_address=http://127.0.0.1:8200 \
  -var "k8s_host=$K8S_HOST" \
  -var "k8s_ca_cert=$K8S_CA_CERT" \
  -var "k8s_reviewer_jwt=$K8S_REVIEWER_JWT"
VAULT_TOKEN length: 28, VAULT_ADDR=http://127.0.0.1:8200
K8S_HOST=https://kubernetes.default.svc.cluster.local
K8S_CA_CERT length: 569
K8S_REVIEWER_JWT length: 941
vault_auth_backend.kubernetes: Refreshing state... [id=kubernetes]
vault_policy.mt_node_provisioner: Refreshing state... [id=mt-node-provisioner-staging]

Terraform used the selected providers to generate the following execution plan. Resource actions are indicated with the following symbols:
  + create
  ~ update in-place

Terraform will perform the following actions:

  # vault_auth_backend.kubernetes will be updated in-place
  ~ resource "vault_auth_backend" "kubernetes" {
      + description     = "Kubernetes auth backend for in-cluster pods (ESO + mt-node Agent Injector)."
      + disable_remount = false
        id              = "kubernetes"
      + tune            = [
          + {
              + allowed_response_headers     = []
              + audit_non_hmac_request_keys  = []
              + audit_non_hmac_response_keys = []
              + default_lease_ttl            = "15m"
              + listing_visibility           = "unauth"
              + max_lease_ttl                = "1h"
              + passthrough_request_headers  = []
                # (1 unchanged attribute hidden)
            },
        ]
        # (4 unchanged attributes hidden)
    }

  # vault_kubernetes_auth_backend_config.kubernetes will be created
  + resource "vault_kubernetes_auth_backend_config" "kubernetes" {
      + backend                           = "kubernetes"
      + disable_iss_validation            = false
      + disable_local_ca_jwt              = false
      + id                                = (known after apply)
      + issuer                            = "https://kubernetes.default.svc.cluster.local"
      + kubernetes_ca_cert                = (sensitive value)
      + kubernetes_host                   = "https://kubernetes.default.svc.cluster.local"
      + token_reviewer_jwt                = (sensitive value)
      + use_annotations_as_alias_metadata = (known after apply)
    }

  # vault_kubernetes_auth_backend_role.mt_node_provisioner will be created
  + resource "vault_kubernetes_auth_backend_role" "mt_node_provisioner" {
      + alias_name_source                = (known after apply)
      + audience                         = "vault"
      + backend                          = "kubernetes"
      + bound_service_account_names      = [
          + "etradie-engine",
        ]
      + bound_service_account_namespaces = [
          + "etradie-system",
        ]
      + id                               = (known after apply)
      + role_name                        = "mt-node-provisioner"
      + token_max_ttl                    = 3600
      + token_period                     = 900
      + token_policies                   = [
          + "mt-node-provisioner-staging",
        ]
      + token_type                       = "default"
    }

  # vault_kubernetes_auth_backend_role.mt_node_tenant will be created
  + resource "vault_kubernetes_auth_backend_role" "mt_node_tenant" {
      + alias_name_source                = "serviceaccount_uid"
      + audience                         = "vault"
      + backend                          = "kubernetes"
      + bound_service_account_names      = [
          + "etradie-mt-*",
        ]
      + bound_service_account_namespaces = [
          + "etradie-system",
        ]
      + id                               = (known after apply)
      + role_name                        = "mt-node-tenant"
      + token_max_ttl                    = 3600
      + token_period                     = 900
      + token_policies                   = [
          + "mt-node-tenant-staging",
        ]
      + token_type                       = "default"
    }

  # vault_kv_secret_v2.billing will be created
  + resource "vault_kv_secret_v2" "billing" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/billing/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.data_layer_chromadb will be created
  + resource "vault_kv_secret_v2" "data_layer_chromadb" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/data-layer/chromadb/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.data_layer_postgres will be created
  + resource "vault_kv_secret_v2" "data_layer_postgres" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/data-layer/postgres/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.data_layer_redis will be created
  + resource "vault_kv_secret_v2" "data_layer_redis" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/data-layer/redis/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.edge_ingress_aop_ca will be created
  + resource "vault_kv_secret_v2" "edge_ingress_aop_ca" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/edge-ingress/staging/cloudflare/aop_ca"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.edge_ingress_maxmind will be created
  + resource "vault_kv_secret_v2" "edge_ingress_maxmind" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/edge-ingress/staging/maxmind"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.edge_ingress_tls will be created
  + resource "vault_kv_secret_v2" "edge_ingress_tls" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/edge-ingress/staging/tls"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.edge_ingress_tunnel will be created
  + resource "vault_kv_secret_v2" "edge_ingress_tunnel" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/edge-ingress/staging/cloudflare/tunnel"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.engine will be created
  + resource "vault_kv_secret_v2" "engine" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/engine/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.execution will be created
  + resource "vault_kv_secret_v2" "execution" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/execution/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.gateway will be created
  + resource "vault_kv_secret_v2" "gateway" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/gateway/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.linkerd_identity will be created
  + resource "vault_kv_secret_v2" "linkerd_identity" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/platform/linkerd/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.management will be created
  + resource "vault_kv_secret_v2" "management" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/management/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_kv_secret_v2.mt_node will be created
  + resource "vault_kv_secret_v2" "mt_node" {
      + data                = (sensitive value)
      + data_json           = (sensitive value)
      + delete_all_versions = false
      + disable_read        = false
      + id                  = (known after apply)
      + metadata            = (known after apply)
      + mount               = "etradie"
      + name                = "etradie/services/mt-node/staging"
      + path                = (known after apply)

      + custom_metadata (known after apply)
    }

  # vault_policy.mt_node_tenant will be created
  + resource "vault_policy" "mt_node_tenant" {
      + id     = (known after apply)
      + name   = "mt-node-tenant-staging"
      + policy = <<-EOT
            path "etradie/data/tenants/mt-node/{{identity.entity.aliases.auth_kubernetes_1f865701.metadata.service_account_name}}" {
              capabilities = ["read"]
            }
        EOT
    }

Plan: 18 to add, 1 to change, 0 to destroy.

Changes to Outputs:
  ~ mt_node_tenant_secrets = {
      ~ provisioner_role   = null -> "mt-node-provisioner"
      ~ tenant_policy      = null -> "mt-node-tenant-staging"
      ~ tenant_role        = null -> "mt-node-tenant"
        # (3 unchanged attributes hidden)
    }
  ~ vault_paths            = {
      + billing              = (known after apply)
      + data_layer_chromadb  = (known after apply)
      + data_layer_postgres  = (known after apply)
      + data_layer_redis     = (known after apply)
      + edge_ingress_aop_ca  = (known after apply)
      + edge_ingress_maxmind = (known after apply)
      + edge_ingress_tls     = (known after apply)
      + edge_ingress_tunnel  = (known after apply)
      + engine               = (known after apply)
      + execution            = (known after apply)
      + gateway              = (known after apply)
      + management           = (known after apply)
      + mt_node              = (known after apply)
    }
vault_kv_secret_v2.mt_node: Creating...
vault_kv_secret_v2.linkerd_identity: Creating...
vault_kv_secret_v2.edge_ingress_tunnel: Creating...
vault_kv_secret_v2.edge_ingress_aop_ca: Creating...
vault_kv_secret_v2.data_layer_redis: Creating...
vault_kv_secret_v2.execution: Creating...
vault_kv_secret_v2.data_layer_chromadb: Creating...
vault_kv_secret_v2.data_layer_postgres: Creating...
vault_kv_secret_v2.gateway: Creating...
vault_kv_secret_v2.management: Creating...
vault_kv_secret_v2.linkerd_identity: Creation complete after 2s [id=etradie/data/etradie/platform/linkerd/staging]
vault_kv_secret_v2.billing: Creating...
vault_kv_secret_v2.execution: Creation complete after 3s [id=etradie/data/etradie/services/execution/staging]
vault_kv_secret_v2.engine: Creating...
vault_kv_secret_v2.edge_ingress_tunnel: Creation complete after 3s [id=etradie/data/etradie/services/edge-ingress/staging/cloudflare/tunnel]
vault_kv_secret_v2.mt_node: Creation complete after 3s [id=etradie/data/etradie/services/mt-node/staging]
vault_kv_secret_v2.data_layer_chromadb: Creation complete after 3s [id=etradie/data/etradie/data-layer/chromadb/staging]
vault_kv_secret_v2.edge_ingress_maxmind: Creating...
vault_kv_secret_v2.edge_ingress_tls: Creating...
vault_kv_secret_v2.data_layer_redis: Creation complete after 3s [id=etradie/data/etradie/data-layer/redis/staging]
vault_auth_backend.kubernetes: Modifying... [id=kubernetes]
vault_kv_secret_v2.data_layer_postgres: Creation complete after 3s [id=etradie/data/etradie/data-layer/postgres/staging]
vault_kv_secret_v2.edge_ingress_aop_ca: Creation complete after 3s [id=etradie/data/etradie/services/edge-ingress/staging/cloudflare/aop_ca]
vault_kv_secret_v2.gateway: Creation complete after 3s [id=etradie/data/etradie/services/gateway/staging]
vault_kv_secret_v2.management: Creation complete after 3s [id=etradie/data/etradie/services/management/staging]
vault_kv_secret_v2.billing: Creation complete after 2s [id=etradie/data/etradie/services/billing/staging]
vault_kv_secret_v2.edge_ingress_maxmind: Creation complete after 1s [id=etradie/data/etradie/services/edge-ingress/staging/maxmind]
vault_kv_secret_v2.engine: Creation complete after 1s [id=etradie/data/etradie/services/engine/staging]
vault_auth_backend.kubernetes: Modifications complete after 1s [id=kubernetes]
vault_kv_secret_v2.edge_ingress_tls: Creation complete after 1s [id=etradie/data/etradie/services/edge-ingress/staging/tls]
vault_kubernetes_auth_backend_role.mt_node_provisioner: Creating...
vault_kubernetes_auth_backend_config.kubernetes: Creating...
vault_policy.mt_node_tenant: Creating...
vault_kubernetes_auth_backend_config.kubernetes: Creation complete after 1s [id=auth/kubernetes/config]
vault_kubernetes_auth_backend_role.mt_node_provisioner: Creation complete after 1s [id=auth/kubernetes/role/mt-node-provisioner]
vault_policy.mt_node_tenant: Creation complete after 1s [id=mt-node-tenant-staging]
vault_kubernetes_auth_backend_role.mt_node_tenant: Creating...
vault_kubernetes_auth_backend_role.mt_node_tenant: Creation complete after 1s [id=auth/kubernetes/role/mt-node-tenant]

Apply complete! Resources: 18 added, 1 changed, 0 destroyed.

Outputs:

mt_node_tenant_secrets = {
  "k8s_auth_backend" = "kubernetes"
  "path_prefix" = "etradie/tenants/mt-node"
  "provisioner_policy" = "mt-node-provisioner-staging"
  "provisioner_role" = "mt-node-provisioner"
  "tenant_policy" = "mt-node-tenant-staging"
  "tenant_role" = "mt-node-tenant"
}
vault_paths = {
  "billing" = "etradie/data/etradie/services/billing/staging"
  "data_layer_chromadb" = "etradie/data/etradie/data-layer/chromadb/staging"
  "data_layer_postgres" = "etradie/data/etradie/data-layer/postgres/staging"
  "data_layer_redis" = "etradie/data/etradie/data-layer/redis/staging"
  "edge_ingress_aop_ca" = "etradie/data/etradie/services/edge-ingress/staging/cloudflare/aop_ca"
  "edge_ingress_maxmind" = "etradie/data/etradie/services/edge-ingress/staging/maxmind"
  "edge_ingress_tls" = "etradie/data/etradie/services/edge-ingress/staging/tls"
  "edge_ingress_tunnel" = "etradie/data/etradie/services/edge-ingress/staging/cloudflare/tunnel"
  "engine" = "etradie/data/etradie/services/engine/staging"
  "execution" = "etradie/data/etradie/services/execution/staging"
  "gateway" = "etradie/data/etradie/services/gateway/staging"
  "management" = "etradie/data/etradie/services/management/staging"
  "mt_node" = "etradie/data/etradie/services/mt-node/staging"
}
softverse@Softverse:~/eTradie/infrastructure/cluster/vault-paths$ kubectl get clustersecretstore vault-backend -o jsonpath='{.spec.provider.vault.path}{"\n"}'
secret
softverse@Softverse:~/eTradie/infrastructure/cluster/vault-paths$ # List the KV paths under the etradie/ mount.
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv list -mount=etradie etradie/

# Read one of the placeholders to confirm it's there (bootstrap value).
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie etradie/services/gateway/staging
Keys
----
data-layer/
platform/
services/
================ Secret Path ================
etradie/data/etradie/services/gateway/staging

======= Metadata =======
Key                Value
---                -----
created_time       2026-06-14T12:48:40.173863755Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            1

====== Data ======
Key          Value
---          -----
bootstrap    placeholder; populate keys: auth_database_url, postgres_user, postgres_password, postgres_host, postgres_port, postgres_db, postgres_sslmode (require/verify-full; consumed by the gateway POSTGRES_* fallback DSN when auth_database_url is unset), gateway_redis_url, auth_jwt_secret, auth_admin_password, engine_internal_shared_secret (must equal etradie/services/engine/staging:engine_internal_shared_secret if you also store it there), billing_internal_shared_secret (MUST EQUAL etradie/services/billing/staging:internal_shared_secret).
softverse@Softverse:~/eTradie/infrastructure/cluster/vault-paths$ cd ~/eTradie
git pull --rebase gitlab main
git push origin main
git log --oneline -5
remote: Enumerating objects: 20, done.
remote: Counting objects: 100% (20/20), done.
remote: Compressing objects: 100% (15/15), done.
remote: Total 15 (delta 12), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (15/15), 6.54 KiB | 57.00 KiB/s, done.
From https://gitlab.com/exoper2/exoper
 * branch              main       -> FETCH_HEAD
   4dc14b18..6fcb0d82  main       -> gitlab/main
Updating 4dc14b18..6fcb0d82
Fast-forward
 docs/runbooks/PROGRESS.md | 65 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 docs/runbooks/README.md   | 48 +++++++++++++++++++++++++++++++++++++++++++-----
 2 files changed, 107 insertions(+), 6 deletions(-)
Enumerating objects: 20, done.
Counting objects: 100% (20/20), done.
Delta compression using up to 4 threads
Compressing objects: 100% (15/15), done.
Writing objects: 100% (15/15), 6.56 KiB | 1.09 MiB/s, done.
Total 15 (delta 12), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (12/12), completed with 5 local objects.
To https://github.com/FlameGreat-1/eTradie.git
   4dc14b18..6fcb0d82  main -> main
6fcb0d82 (HEAD -> main, origin/main, gitlab/main) docs(runbooks): PROGRESS.md — add explicit next-action block for §8.1.B→§8.2 transition
b33ec3f1 docs(runbooks): record Phase 8.1 outcome + the mount-mismatch incident
f3408a65 docs(runbooks): add etradie/ KV-v2 mount to README §3.4 + ClusterSecretStore alignment in §4.2
4dc14b18 updated
fb9364c8 updated
softverse@Softverse:~/eTradie$ kubectl patch clustersecretstore vault-backend --type=merge \
  -p '{"spec":{"provider":{"vault":{"path":"etradie"}}}}'

# Verify the patch took.
kubectl get clustersecretstore vault-backend \
  -o jsonpath='{.spec.provider.vault.path} {.status.conditions[0].reason}{"\n"}'
# expect: etradie Valid
clustersecretstore.external-secrets.io/vault-backend patched
etradie Valid
softverse@Softverse:~/eTradie$ cd ~/eTradie
pwd
echo "KUBECONFIG=$KUBECONFIG"
echo "ROOT_TOKEN length: ${#ROOT_TOKEN} chars (expect 28)"
kubectl get nodes
/home/softverse/eTradie
KUBECONFIG=/home/softverse/.kube/etradie-contabo.yaml
ROOT_TOKEN length: 28 chars (expect 28)
NAME         STATUS   ROLES                  AGE   VERSION
vmi3362776   Ready    control-plane,master   13h   v1.30.4+k3s1
softverse@Softverse:~/eTradie$ cd ~/eTradie

# === §8.2 — Generate shared secrets ONCE ===

DB_PASS=$(openssl rand -hex 32)
REDIS_PASS=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 64)            # 128 hex chars
BROKER_KEY=$(openssl rand -hex 32)            # Tier 3 KEK, engine-only
CHROMA_TOKEN=$(openssl rand -hex 32)
ADMIN_PASS=$(openssl rand -hex 24)            # 48 hex chars; rotate after first login
ENGINE_SHARED=$(openssl rand -hex 32)         # X-Internal-Auth: callers → engine
BILLING_SHARED=$(openssl rand -hex 32)        # X-Internal-Auth: gateway → billing
MT_DEFAULT_ZMQ=$(openssl rand -hex 32)

# DSN construction (sslmode=require — engine + billing fail-closed otherwise).
DB_URL_GO="postgres://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=require"
DB_URL_PY="postgresql+asyncpg://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=require"
REDIS0="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/0"
REDIS1="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/1"

echo "=== §8.2 length sanity checks (no values echoed) ==="
echo "DB_PASS=${#DB_PASS} (expect 64) $( [ ${#DB_PASS} -eq 64 ] && echo OK || echo FAIL )"
echo "REDIS_PASS=${#REDIS_PASS} (expect 64) $( [ ${#REDIS_PASS} -eq 64 ] && echo OK || echo FAIL )"
echo "JWT_SECRET=${#JWT_SECRET} (expect 128) $( [ ${#JWT_SECRET} -eq 128 ] && echo OK || echo FAIL )"
echo "BROKER_KEY=${#BROKER_KEY} (expect 64) $( [ ${#BROKER_KEY} -eq 64 ] && echo OK || echo FAIL )"
echo "CHROMA_TOKEN=${#CHROMA_TOKEN} (expect 64) $( [ ${#CHROMA_TOKEN} -eq 64 ] && echo OK || echo FAIL )"
echo "ADMIN_PASS=${#ADMIN_PASS} (expect 48) $( [ ${#ADMIN_PASS} -eq 48 ] && echo OK || echo FAIL )"
echo "ENGINE_SHARED=${#ENGINE_SHARED} (expect 64) $( [ ${#ENGINE_SHARED} -eq 64 ] && echo OK || echo FAIL )"
echo "BILLING_SHARED=${#BILLING_SHARED} (expect 64) $( [ ${#BILLING_SHARED} -eq 64 ] && echo OK || echo FAIL )"
echo "MT_DEFAULT_ZMQ=${#MT_DEFAULT_ZMQ} (expect 64) $( [ ${#MT_DEFAULT_ZMQ} -eq 64 ] && echo OK || echo FAIL )"

# === §8.3 — Persist to ~/etradie-staging-creds.txt BEFORE any vault writes ===

umask 077
cat > ~/etradie-staging-creds.txt <<EOF
# eTradie §8.2 generated secrets — staging — $(date -u +%FT%TZ)
# mode 0600. Workstation safety net until Phase 15 Vault Raft snapshots.
# Vault remains canonical; this file is the recovery reference.
DB_PASS=${DB_PASS}
REDIS_PASS=${REDIS_PASS}
echo "=== §8.2 + §8.3 complete; helpers defined; ready for §8.4 ==="\ port-forward needed) ===
=== §8.2 length sanity checks (no values echoed) ===
DB_PASS=64 (expect 64) OK
REDIS_PASS=64 (expect 64) OK
JWT_SECRET=128 (expect 128) OK
BROKER_KEY=64 (expect 64) OK
CHROMA_TOKEN=64 (expect 64) OK
ADMIN_PASS=48 (expect 48) OK
ENGINE_SHARED=64 (expect 64) OK
BILLING_SHARED=64 (expect 64) OK
MT_DEFAULT_ZMQ=64 (expect 64) OK
-rw------- 1 softverse softverse 950 Jun 14 14:08 /home/softverse/etradie-staging-creds.txt
OK §8.3 creds file written, mode 0600
vkv is a function
vkv ()
{
    kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault kv put "$@"
}
vkv_get is a function
vkv_get ()
{
    kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault kv get "$@"
}
vkv_file is a function
vkv_file ()
{
    local path="$1";
    shift;

=== §8.2 + §8.3 complete; helpers defined; ready for §8.4 ===
softverse@Softverse:~/eTradie$ cd ~/eTradie

# === §8.4 — Data-layer Vault paths ===

echo "=== §8.4 — writing data-layer paths ==="

# 8.4.1 — Postgres: 3 properties.
vkv etradie/data-layer/postgres/staging \
  postgres_user=etradie \
  postgres_db=etradie \
  postgres_password="${DB_PASS}"

# 8.4.2 — Redis: 1 property.
vkv etradie/data-layer/redis/staging \
  redis_password="${REDIS_PASS}"

# 8.4.3 — ChromaDB: 1 property. SINGLE source of truth — both the
# chromadb StatefulSet AND the engine pod read this exact path.
vkv etradie/data-layer/chromadb/staging \
  auth_token="${CHROMA_TOKEN}"

echo ""
echo "=== §8.4 read-back verification (length-only, no values echoed) ==="

# Postgres read-back — check 3 properties all present.
pg_user=$(vkv_get -field=postgres_user etradie/data-layer/postgres/staging 2>/dev/null)
pg_db=$(vkv_get -field=postgres_db etradie/data-layer/postgres/staging 2>/dev/null)
pg_pass_len=$(vkv_get -field=postgres_password etradie/data-layer/postgres/staging 2>/dev/null | wc -c)
echo "postgres/staging: user=${pg_user} db=${pg_db} password_length=${pg_pass_len} (expect 64)"

# Redis read-back.
redis_pass_len=$(vkv_get -field=redis_password etradie/data-layer/redis/staging 2>/dev/null | wc -c)
echo "redis/staging: password_length=${redis_pass_len} (expect 64)"

# ChromaDB read-back.
chroma_len=$(vkv_get -field=auth_token etradie/data-layer/chromadb/staging 2>/dev/null | wc -c)
echo "chromadb/staging: auth_token_length=${chroma_len} (expect 64)"

# Hash-compare DB_PASS in shell against what Vault returned (no value leak).
shell_hash=$(printf '%s' "${DB_PASS}" | sha256sum | cut -d' ' -f1)
[ "$shell_hash" = "$vault_hash" ] && echo "  OK MATCH (Vault holds exactly what was generated)" || echo "  FAIL MISMATCH")
=== §8.4 — writing data-layer paths ===
============== Secret Path ==============
etradie/data/data-layer/postgres/staging

======= Metadata =======
Key                Value
---                -----
created_time       2026-06-14T13:09:29.378902664Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            1
============ Secret Path ============
etradie/data/data-layer/redis/staging

======= Metadata =======
Key                Value
---                -----
created_time       2026-06-14T13:09:31.359957153Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            1
============== Secret Path ==============
etradie/data/data-layer/chromadb/staging

======= Metadata =======
Key                Value
---                -----
created_time       2026-06-14T13:09:33.916229283Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            1

=== §8.4 read-back verification (length-only, no values echoed) ===
postgres/staging: user=etradie db=etradie password_length=64 (expect 64)
redis/staging: password_length=64 (expect 64)
chromadb/staging: auth_token_length=64 (expect 64)

DB_PASS equality check:
  shell hash:  61f37c14c80f2235a540b73b9c968abf32ec7e5e0b1a468ac44723547b97d5de
  vault hash:  61f37c14c80f2235a540b73b9c968abf32ec7e5e0b1a468ac44723547b97d5de
  OK MATCH (Vault holds exactly what was generated)
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$ # What §8.4 actually wrote (no etradie/ prefix in the path arg):
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie data-layer/postgres/staging 2>&1 | head -20

# What the chart ExternalSecret will read (with etradie/ prefix in the key,
# which is what terraform created):
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie etradie/data-layer/postgres/staging 2>&1 | head -20
============== Secret Path ==============
etradie/data/data-layer/postgres/staging

======= Metadata =======
Key                Value
---                -----
created_time       2026-06-14T13:09:29.378902664Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            1

========== Data ==========
Key                  Value
---                  -----
postgres_db          etradie
postgres_password    ec7461b724a9181f4f248bc7bb5224d828f03eec83f6eee4c37b56e503c4301d
postgres_user        etradie
================== Secret Path ==================
etradie/data/etradie/data-layer/postgres/staging

======= Metadata =======
Key                Value
---                -----
created_time       2026-06-14T12:48:40.162988688Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            1

====== Data ======
Key          Value
---          -----
bootstrap    placeholder; populate with postgres_user, postgres_db, postgres_password BEFORE the data-layer chart is reconciled (postgres pod blocks otherwise)
softverse@Softverse:~/eTradie$