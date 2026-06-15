
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

AND WE HAVE DONE PHASE 0, 1, 2, 3, 4, 5, 6, 7, 8 AND 9 AS YOU CAN SEE IN THE /docs/runbooks/README.md AND THE /docs/runbooks/PROGRESS.md

SO YOU EXAMINE BOTH FILES THOROUGHLY FROM THE BEGINNING TO THE END.

 EXAMINE IT  THOROUGHLY FROM  THE BEGINNING TO THE END BECAUSE YOU NEED TO UNDERSTAND AND KNOW HOW TO PICK UP FROM WHERE WE STOPPED

 SO WE ARE GOING TO CONTINUE WITH PHASE 10 THIS IS WHAT YOU SAID LAST IN THE PREVIOUS SESSION:




se:/eTradie$ chmod 600 ~/.ghcr_pull_pat
softverse@Softverse:/eTradie$
softverse@Softverse:~/eTradie$ ls -la ~/.ghcr_pull_pat
wc -c ~/.ghcr_pull_pat
head -c 4 ~/.ghcr_pull_pat; echo "  ← expect: ghp_"
Confirm scopes are read:packages only.
echo ""
echo "=== new PAT scopes ==="
curl -sSI -u "flamegreat-1:$(cat ~/.ghcr_pull_pat)" https://api.github.com/user   | grep -i 'x-oauth-scopes'
expect: x-oauth-scopes: read:packages
Confirm it can actually pull.
echo ""
echo "=== test pull with the new PAT ==="
docker logout ghcr.io 2>/dev/null
cat ~/.ghcr_pull_pat | docker login ghcr.io -u flamegreat-1 --password-stdin 2>&1 | tail -3
docker pull ghcr.io/flamegreat-1/etradie/engine:staging-0.1.0 2>&1 | tail -3
docker logout ghcr.io 2>/dev/null
-rw------- 1 softverse softverse 41 Jun 14 16:48 /home/softverse/.ghcr_pull_pat
41 /home/softverse/.ghcr_pull_pat
ghp_  ← expect: ghp_
=== new PAT scopes ===
x-oauth-scopes: read:packages
access-control-expose-headers: ETag, Link, Location, Retry-After, X-GitHub-OTP, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Used, X-RateLimit-Resource, X-RateLimit-Reset, X-OAuth-Scopes, X-Accepted-OAuth-Scopes, X-Poll-Interval, X-GitHub-Media-Type, X-GitHub-SSO, X-GitHub-Request-Id, Deprecation, Sunset, Warning
=== test pull with the new PAT ===
Removing login credentials for ghcr.io
https://docs.docker.com/go/credential-store/
Login Succeeded


All three checks green:

File mode 0600, 41 bytes (ghp_ + 36 char + newline) ✓
Scopes line: x-oauth-scopes: read:packages — exactly one scope, the right one ✓
Login Succeeded ✓ (the actual pull output got cut off again but login alone proves auth works)

The PAT is good. Now Phase 10.0 — pre-creating namespaces and the ghcr-pull Secret on the cluster.
Phase 10.0 — Pre-flight (namespaces + ghcr-pull Secret per namespace)
This runs through the SSH tunnel against the VPS K3s cluster. Verify the tunnel is up first — if kubectl get nodes hangs you need to reopen the tunnel terminal.

Copy to clipboard
Insert at cursor
cd ~/eTradie

# === §10.0.1 — tunnel + kubeconfig sanity ===
echo "=== §10.0.1 — tunnel + KUBECONFIG ==="
[ -z "$KUBECONFIG" ] && export KUBECONFIG=~/.kube/etradie-contabo.yaml
echo "  KUBECONFIG=$KUBECONFIG"
kubectl get nodes 2>&1 | head -3
echo ""

# === §10.0.2 — create the two namespaces ESO + apps will use ===
# data-layer chart creates etradie-system itself at Phase 12, but we
# need it NOW to drop the ghcr-pull Secret into. Pre-creating is
# idempotent: ArgoCD's CreateNamespace=true syncOption is a no-op
# when the namespace already exists. Same for edge-ingress-system.
echo "=== §10.0.2 — namespaces ==="
for ns in etradie-system edge-ingress-system; do
  kubectl get ns "$ns" >/dev/null 2>&1 \
    && echo "  $ns already exists" \
    || { kubectl create namespace "$ns" && echo "  $ns created"; }
done
kubectl get ns etradie-system edge-ingress-system

# === §10.0.3 — ghcr-pull Secret in each namespace ===
# Type: kubernetes.io/dockerconfigjson — what containerd expects for
# imagePullSecrets. Username MUST be the GHCR login name
# (flamegreat-1, lowercase per GHCR's case-sensitive rule). Email is
# required by the format but only used for the dockerconfigjson
# auth-entry encoding — not validated by GHCR. Use the GHCR docs'
# canonical placeholder: not-needed@github.com.
echo ""
echo "=== §10.0.3 — ghcr-pull Secret in each namespace ==="
GHCR_PAT=$(cat ~/.ghcr_pull_pat)

for ns in etradie-system edge-ingress-system; do
  # Idempotent: delete first if present, then re-create.
  kubectl -n "$ns" delete secret ghcr-pull --ignore-not-found
  kubectl -n "$ns" create secret docker-registry ghcr-pull \
    --docker-server=ghcr.io \
    --docker-username=flamegreat-1 \
    --docker-password="$GHCR_PAT" \
    --docker-email=not-needed@github.com
done
unset GHCR_PAT
echo ""

# === §10.0.4 — verify the Secret bytes decode correctly ===
echo "=== §10.0.4 — verify dockerconfigjson decode (per namespace) ==="
for ns in etradie-system edge-ingress-system; do
  echo "--- $ns ---"
  kubectl -n "$ns" get secret ghcr-pull -o jsonpath='{.data.\.dockerconfigjson}' \
    | base64 -d \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
auth = d['auths']['ghcr.io']
import base64
user, _, pw = base64.b64decode(auth['auth']).decode().partition(':')
print(f'  server  : ghcr.io')
print(f'  username: {user}')
print(f'  password: {pw[:4]}... ({len(pw)} chars)')
print(f'  email   : {auth.get(\"email\", \"(none)\")}')"
done

# === §10.0.5 — Final state check ===
echo ""
echo "=== §10.0.5 — final state ==="
kubectl get secret -n etradie-system ghcr-pull -o jsonpath='{.type}{"\n"}'
kubectl get secret -n edge-ingress-system ghcr-pull -o jsonpath='{.type}{"\n"}'
# both should print: kubernetes.io/dockerconfigjson

What to expect

kubectl get nodes shows vmi3362776 Ready ... v1.30.4+k3s1 ✓
2 namespaces created (or "already exists") ✓
2 secret/ghcr-pull created lines ✓
Decode block shows server: ghcr.io, username: flamegreat-1, password: ghp_... (40 chars), email: not-needed@github.com for each namespace ✓
Both secrets type kubernetes.io/dockerconfigjson ✓



$
softverse@Softverse:~/eTradie$ echo "=== §10.1 — Install ArgoCD v2.13.3 ==="

# 1. Create the argocd namespace (idempotent).
kubectl get ns argocd >/dev/null 2>&1 \
  && echo "  argocd namespace already exists" \
  || kubectl create namespace argocd

# 2. Apply ArgoCD v2.13.3 install manifest.
echo ""
echo "=== applying ArgoCD v2.13.3 manifest ==="
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml

# 3. Wait for argocd-server Deployment to become Available.
echo ""
echo "=== waiting for argocd-server (up to 5 min) ==="
kubectl -n argocd wait --for=condition=Available deployment/argocd-server --timeout=300s

# 4. State check — every ArgoCD component pod status.
echo ""
echo "=== argocd namespace state ==="
kubectl -n argocd get pods
echo ""
echo "=== argocd deployments (all should be Available) ==="
kubectl -n argocd get deploy
echo ""
echo "=== argocd statefulsets (application-controller is a StatefulSet) ==="
kubectl -n argocd get sts
=== §10.1 — Install ArgoCD v2.13.3 ===
namespace/argocd created

=== applying ArgoCD v2.13.3 manifest ===
customresourcedefinition.apiextensions.k8s.io/applications.argoproj.io created
customresourcedefinition.apiextensions.k8s.io/applicationsets.argoproj.io created
customresourcedefinition.apiextensions.k8s.io/appprojects.argoproj.io created
serviceaccount/argocd-application-controller created
serviceaccount/argocd-applicationset-controller created
serviceaccount/argocd-dex-server created
serviceaccount/argocd-notifications-controller created
serviceaccount/argocd-redis created
serviceaccount/argocd-repo-server created
serviceaccount/argocd-server created
role.rbac.authorization.k8s.io/argocd-application-controller created
role.rbac.authorization.k8s.io/argocd-applicationset-controller created
role.rbac.authorization.k8s.io/argocd-dex-server created
role.rbac.authorization.k8s.io/argocd-notifications-controller created
role.rbac.authorization.k8s.io/argocd-redis created
role.rbac.authorization.k8s.io/argocd-server created
clusterrole.rbac.authorization.k8s.io/argocd-application-controller created
clusterrole.rbac.authorization.k8s.io/argocd-applicationset-controller created
clusterrole.rbac.authorization.k8s.io/argocd-server created
rolebinding.rbac.authorization.k8s.io/argocd-application-controller created
rolebinding.rbac.authorization.k8s.io/argocd-applicationset-controller created
rolebinding.rbac.authorization.k8s.io/argocd-dex-server created
rolebinding.rbac.authorization.k8s.io/argocd-notifications-controller created
rolebinding.rbac.authorization.k8s.io/argocd-redis created
rolebinding.rbac.authorization.k8s.io/argocd-server created
clusterrolebinding.rbac.authorization.k8s.io/argocd-application-controller created
clusterrolebinding.rbac.authorization.k8s.io/argocd-applicationset-controller created
clusterrolebinding.rbac.authorization.k8s.io/argocd-server created
configmap/argocd-cm created
configmap/argocd-cmd-params-cm created
configmap/argocd-gpg-keys-cm created
configmap/argocd-notifications-cm created
configmap/argocd-rbac-cm created
configmap/argocd-ssh-known-hosts-cm created
configmap/argocd-tls-certs-cm created
secret/argocd-notifications-secret created
secret/argocd-secret created
service/argocd-applicationset-controller created
service/argocd-dex-server created
service/argocd-metrics created
service/argocd-notifications-controller-metrics created
service/argocd-redis created
service/argocd-repo-server created
service/argocd-server created
service/argocd-server-metrics created
deployment.apps/argocd-applicationset-controller created
deployment.apps/argocd-dex-server created
deployment.apps/argocd-notifications-controller created
deployment.apps/argocd-redis created
deployment.apps/argocd-repo-server created
deployment.apps/argocd-server created
statefulset.apps/argocd-application-controller created
networkpolicy.networking.k8s.io/argocd-application-controller-network-policy created
networkpolicy.networking.k8s.io/argocd-applicationset-controller-network-policy created
networkpolicy.networking.k8s.io/argocd-dex-server-network-policy created
networkpolicy.networking.k8s.io/argocd-notifications-controller-network-policy created
networkpolicy.networking.k8s.io/argocd-redis-network-policy created
networkpolicy.networking.k8s.io/argocd-repo-server-network-policy created
networkpolicy.networking.k8s.io/argocd-server-network-policy created

=== waiting for argocd-server (up to 5 min) ===
deployment.apps/argocd-server condition met

=== argocd namespace state ===
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          30s
argocd-applicationset-controller-66db6984c8-rrtj9   1/1     Running   0          38s
argocd-dex-server-647484ccbb-fcn7p                  1/1     Running   0          37s
argocd-notifications-controller-7f955f9677-nvvxf    1/1     Running   0          36s
argocd-redis-6f68b7d98f-dkrp4                       1/1     Running   0          35s
argocd-repo-server-7d677cd7c5-82xtp                 1/1     Running   0          34s
argocd-server-564b8cdd98-qw5ct                      1/1     Running   0          32s

=== argocd deployments (all should be Available) ===
NAME                               READY   UP-TO-DATE   AVAILABLE   AGE
argocd-applicationset-controller   1/1     1            1           39s
argocd-dex-server                  1/1     1            1           38s
argocd-notifications-controller    1/1     1            1           37s
argocd-redis                       1/1     1            1           36s
argocd-repo-server                 1/1     1            1           35s
argocd-server                      1/1     1            1           33s

=== argocd statefulsets (application-controller is a StatefulSet) ===
NAME                            READY   AGE
argocd-application-controller   1/1     32s
softverse@Softverse:~/eTradie$ cd ~/eTrad

Phase 10.0 fully closed. Status:

- Tunnel reopened, `vmi3362776 Ready` ✓
- Both namespaces created (`etradie-system`, `edge-ingress-system`) ✓
- `ghcr-pull` Secret created in each ✓
- dockerconfigjson decodes correctly: server=ghcr.io, username=flamegreat-1, 40-char password starting `ghp_` ✓
- Both secrets type `kubernetes.io/dockerconfigjson` ✓

About the `ssh-agent` warning — your tunnel terminal had to re-authenticate without the agent. Not blocking us, but worth noting: when you reopened the tunnel terminal you typed the passphrase manually instead of using `ssh-add`. That's fine for one session; if you re-source `~/.bashrc` or `ssh-add ~/.ssh/id_ed25519` in any terminal, future tunnels will go passphrase-free again.

Pre-Phase 10 work is fully done:
- Trust anchor PEM committed to git (`fc9e0042`)
- imagePullSecrets wired in 6 chart values (`fc9e0042`)
- GHCR read-only PAT generated and stored at `~/.ghcr_pull_pat`
- Both namespaces exist on the cluster
- `ghcr-pull` Secret exists in both namespaces

#### Now: Phase 10.1 — Install ArgoCD on the cluster

Three things this does:
1. Creates the `argocd` namespace
2. Applies the official ArgoCD v2.13.3 install manifest (CRDs, controllers, RBAC, services)
3. Waits for `argocd-server` to become Available

```bash
echo "=== §10.1 — Install ArgoCD v2.13.3 ==="

# 1. Create the argocd namespace (idempotent).
kubectl get ns argocd >/dev/null 2>&1 \
  && echo "  argocd namespace already exists" \
  || kubectl create namespace argocd

# 2. Apply ArgoCD v2.13.3 install manifest.
echo ""
echo "=== applying ArgoCD v2.13.3 manifest ==="
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml

# 3. Wait for argocd-server Deployment to become Available.
echo ""
echo "=== waiting for argocd-server (up to 5 min) ==="
kubectl -n argocd wait --for=condition=Available deployment/argocd-server --timeout=300s

# 4. State check — every ArgoCD component pod status.
echo ""
echo "=== argocd namespace state ==="
kubectl -n argocd get pods
echo ""
echo "=== argocd deployments (all should be Available) ==="
kubectl -n argocd get deploy
echo ""
echo "=== argocd statefulsets (application-controller is a StatefulSet) ==="
kubectl -n argocd get sts
```

#### What to expect (give it 2-5 minutes for image pulls)

- `argocd` namespace created
- The apply produces about 60 lines of output: many `customresourcedefinition` lines, `serviceaccount`, `role`, `rolebinding`, `clusterrole`, `clusterrolebinding`, `configmap`, `secret`, `service`, `deployment`, `statefulset`, `networkpolicy` entries
- `deployment.apps/argocd-server condition met` from the wait
- 7 pods Running, 1/1:
  - `argocd-application-controller-0` (StatefulSet)
  - `argocd-applicationset-controller-...`
  - `argocd-dex-server-...`
  - `argocd-notifications-controller-...`
  - `argocd-redis-...`
  - `argocd-repo-server-...`
  - `argocd-server-...`

#### If it fails

- **`ImagePullBackOff` on any pod**: ArgoCD images come from Quay/Docker Hub, not GHCR. They're public so this shouldn't happen — but if it does, paste the failing pod's `kubectl describe`.
- **Stuck `Pending`**: usually resource quota or scheduling. `kubectl describe pod <name> -n argocd` shows the reason.
- **Timeout on the wait**: ArgoCD takes ~3-5 min on first install (image pull + startup). If timeout hits, run `kubectl -n argocd get pods` to see what's still pulling/starting.

Paste back the output once it settles. After this, Phase 10.2 (extract admin password + port-forward) is a 30-second step.


Both docs commits confirmed on `main`:

- `4b4ca12e` — PROGRESS.md: Phase 10 in-flight checkpoint (pre-flight + §10.0 + §10.1 complete; §10.2–§10.5 pending)
- `8cbcc19c` — README.md §10: staging-canonical restructure (new §10.0 pre-flight, removed §10.4, new §10.5 Linkerd manual sync)

The repo now captures everything a session-resume operator needs to pick up at §10.2 without re-deriving any state.

Before moving forward — one important point about the **GitHub remote**:

ArgoCD reads from GitHub at §10.3, not GitLab. The two docs commits I just pushed are on the GitLab mirror only (because I push via MCP, which is GitLab-only). The README §10.0 references `git push origin main` (GitHub) as load-bearing — but that applies to **code/value changes** that ArgoCD reconciles. Pure docs commits (PROGRESS.md + README.md) don't affect cluster state, so the GitLab-only mirror is fine for these two specifically.

That said, for full mirror parity, run this on your workstation when convenient:

```bash
cd ~/eTradie
git fetch gitlab main
git pull --rebase gitlab main
git push origin main
```

This pulls the two MCP commits onto your local `main` and pushes them to GitHub so both remotes stay at the same SHA. Not blocking §10.2.

#### Now: Phase 10.2 — Admin password + port-forward + argocd CLI login

This unlocks `argocd app sync` / `argocd app list` for §10.5 (Linkerd manual sync) and Phase 12.

```bash
echo "=== §10.2 — ArgoCD admin password + port-forward + CLI login ==="

# 1. Retrieve the auto-generated admin password.
ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)
echo "  admin password length: ${#ADMIN_ARGO_PWD} chars (not echoed)"
[ ${#ADMIN_ARGO_PWD} -ge 16 ] && echo "  OK (auto-generated argocd password is typically 22+ chars)" \
  || echo "  FAIL (password too short — check the Secret)"
```

After that prints OK, run the rest in two terminals (the port-forward needs to stay running):

**Terminal A — port-forward (leave it running, no prompt returns):**

```bash
[ -z "$KUBECONFIG" ] && export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl -n argocd port-forward svc/argocd-server 8080:443
# (leave this terminal open; it will print "Forwarding from 127.0.0.1:8080 -> 8080")
```

**Terminal B — CLI login (your working terminal):**

```bash
# Verify argocd CLI is on PATH.
which argocd && argocd version --client | head -2

# Retrieve the password again in this terminal.
ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)

# Login.
argocd login 127.0.0.1:8080 \
  --username admin \
  --password "$ADMIN_ARGO_PWD" \
  --insecure

# Verify session.
echo ""
echo "=== argocd CLI session ==="
argocd account list
echo ""
echo "=== argocd version (server) ==="
argocd version | head -4

# Wipe the password from environment.
unset ADMIN_ARGO_PWD
```

#### What to expect

- Password length: 22+ chars
- `Forwarding from 127.0.0.1:8080 -> 8080` (and `Handling connection for 8080` as the login dials)
- `argocd login` returns: `'admin:login' logged in successfully` + `Context '127.0.0.1:8080' updated`
- `argocd account list` shows: `admin true true` (NAME, ENABLED, CAPABILITIES)
- `argocd version` shows both client and server versions — server must be `v2.13.3`

#### Common gotchas

- **`argocd: command not found`** → CLI not installed. Install: `curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/download/v2.13.3/argocd-linux-amd64 && sudo install -m 555 /tmp/argocd /usr/local/bin/argocd`
- **`connection refused` on login** → port-forward terminal closed or not yet listening. In Terminal A, confirm `Forwarding from 127.0.0.1:8080 -> 8080` is printed.
- **`x509: certificate signed by unknown authority`** → missing `--insecure`. The port-forward presents argocd-server's self-signed cert; `--insecure` skips verification (safe for localhost).
- **`tls: failed to verify certificate`** → same as above; ensure `--insecure` is on the command.

Paste back Terminal B's output once `argocd account list` succeeds. After that, §10.3 (apply both AppProjects + root-app) is a 3-command step that immediately cascades and creates every Application — that's the point where we need to be ready to manually sync the Linkerd apps within ~3 min.







-controller   1/1     1            1           39s
argocd-dex-server                  1/1     1            1           38s
argocd-notifications-controller    1/1     1            1           37s
argocd-redis                       1/1     1            1           36s
argocd-repo-server                 1/1     1            1           35s
argocd-server                      1/1     1            1           33s

=== argocd statefulsets (application-controller is a StatefulSet) ===
NAME                            READY   AGE
argocd-application-controller   1/1     32s
softverse@Softverse:~/eTradie$ cd ~/eTradie
git fetch gitlab main
git pull --rebase gitlab main
git push origin main
remote: Enumerating objects: 15, done.
remote: Counting objects: 100% (15/15), done.
remote: Compressing objects: 100% (10/10), done.
remote: Total 10 (delta 8), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (10/10), 13.08 KiB | 8.00 KiB/s, done.
From https://gitlab.com/exoper2/exoper
 * branch              main       -> FETCH_HEAD
   fc9e0042..8cbcc19c  main       -> gitlab/main
From https://gitlab.com/exoper2/exoper
 * branch              main       -> FETCH_HEAD
Updating fc9e0042..8cbcc19c
Fast-forward
 docs/runbooks/PROGRESS.md | 108 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 docs/runbooks/README.md   | 211 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---------
 2 files changed, 304 insertions(+), 15 deletions(-)
Enumerating objects: 15, done.
Counting objects: 100% (15/15), done.
Delta compression using up to 4 threads
Compressing objects: 100% (10/10), done.
Writing objects: 100% (10/10), 13.14 KiB | 2.19 MiB/s, done.
Total 10 (delta 8), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (8/8), completed with 5 local objects.
To https://github.com/FlameGreat-1/eTradie.git
   fc9e0042..8cbcc19c  main -> main
softverse@Softverse:~/eTradie$ echo "=== §10.2 — ArgoCD admin password + port-forward + CLI login ==="

# 1. Retrieve the auto-generated admin password.
ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)
echo "  admin password length: ${#ADMIN_ARGO_PWD} chars (not echoed)"
[ ${#ADMIN_ARGO_PWD} -ge 16 ] && echo "  OK (auto-generated argocd password is typically 22+ chars)" \
  || echo "  FAIL (password too short — check the Secret)"
=== §10.2 — ArgoCD admin password + port-forward + CLI login ===
  admin password length: 16 chars (not echoed)
  OK (auto-generated argocd password is typically 22+ chars)
softverse@Softverse:~/eTradie$ [ -z "$KUBECONFIG" ] && export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl -n argocd port-forward svc/argocd-server 8080:443
# (leave this terminal open; it will print "Forwarding from 127.0.0.1:8080 -> 8080")
Forwarding from 127.0.0.1:8080 -> 8080
Forwarding from [::1]:8080 -> 8080
Handling connection for 8080
Handling connection for 8080
Handling connection for 8080
Handling connection for 8080
E0614 17:12:16.778427  598436 portforward.go:385] error copying from remote stream to local connection: readfrom tcp4 127.0.0.1:8080->127.0.0.1:41772: write tcp4 127.0.0.1:8080->127.0.0.1:41772: write: broken pipe
Handling connection for 8080
Handling connection for 8080
E0614 17:12:19.903348  598436 portforward.go:385] error copying from remote stream to local connection: readfrom tcp4 127.0.0.1:8080->127.0.0.1:41792: write tcp4 127.0.0.1:8080->127.0.0.1:41792: write: broken pipe
Handling connection for 8080
E0614 17:12:21.595505  598436 portforward.go:385] error copying from remote stream to local connection: readfrom tcp4 127.0.0.1:8080->127.0.0.1:41804: write tcp4 127.0.0.1:8080->127.0.0.1:41804: write: broken pipe
Handling connection for 8080
E0614 17:12:22.811268  598436 portforward.go:385] error copying from remote stream to local connection: readfrom tcp4 127.0.0.1:8080->127.0.0.1:56674: write tcp4 127.0.0.1:8080->127.0.0.1:56674: write: broken pipe
Handling connection for 8080
E0614 17:12:24.206619  598436 portforward.go:385] error copying from remote stream to local connection: readfrom tcp4 127.0.0.1:8080->127.0.0.1:56684: write tcp4 127.0.0.1:8080->127.0.0.1:56684: write: broken pipe



erse:~/eTradie/infrastructure$ cd ..
softverse@Softverse:~/eTradie$ # Verify argocd CLI is on PATH.
which argocd && argocd version --client | head -2

# Retrieve the password again in this terminal.
ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)

# Login.
argocd login 127.0.0.1:8080 \
  --username admin \
  --password "$ADMIN_ARGO_PWD" \
  --insecure

# Verify session.
echo ""
echo "=== argocd CLI session ==="
argocd account list
echo ""
echo "=== argocd version (server) ==="
argocd version | head -4

# Wipe the password from environment.
unset ADMIN_ARGO_PWD
/usr/local/bin/argocd
argocd: v2.13.3+a25c8a0
  BuildDate: 2025-01-03T19:06:52Z
'admin:login' logged in successfully
Context '127.0.0.1:8080' updated

=== argocd CLI session ===
NAME   ENABLED  CAPABILITIES
admin  true     login

=== argocd version (server) ===
argocd: v2.13.3+a25c8a0
  BuildDate: 2025-01-03T19:06:52Z
  GitCommit: a25c8a0eef7830be0c2c9074c92dbea8ff23a962
  GitTreeState: clean
softverse@Softverse:~/eTradie$