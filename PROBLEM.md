Examined thoroughly. Two distinct things here — one is a non-issue, one is the real diagnosis.

#### The two `SharedResourceWarning`s — why they didn't clear

The hard-refresh didn't drop them because there are still **two live `edge-ingress` ReplicaSets/pods** both claiming the same resources:

```
edge-ingress-58bcddf595-z2g78   0/2   Init:CrashLoopBackOff   105m
edge-ingress-86c448f965-4hhbz   0/2   Init:CrashLoopBackOff   107m
```

Two different pod-template hashes (`58bcddf595` and `86c448f965`) = two ReplicaSets. The newer one (from the !146 GeoIP chart change reconciling in) is trying to roll out, but the old one can't be torn down because **neither pod ever reaches Ready** — so the rollout is wedged with both alive, and ArgoCD still sees overlapping ownership → `SharedResourceWarning` persists. It'll clear once edge-ingress actually rolls to a single Ready pod. So that warning is a *symptom* of the CrashLoop, not the prune. (The `monitoring-stack(5)` one is just slower cache; ignore it for now — it's `Synced/Healthy`.)

#### The real diagnosis — and it's NOT what !146 fully fixed

This is the critical finding. The `geoip-downloader` init container is **still `maxmindinc/geoipupdate:v6.0`** and still CrashLooping (25 restarts).

But !146 was supposed to replace that init container with a **busybox-based, idempotent, fault-tolerant** one (`geoip.bootstrapInitImage: "busybox:1.36"`) that skips the download if a cached DB exists on the PVC and only hard-fails on a true cold start. What's running on the cluster is the **OLD** init container (`maxmindinc/geoipupdate:v6.0`), which means **the !146 chart change has NOT actually rolled into these pods yet.**

Two possible reasons — we need to find which:

1. **ArgoCD hasn't synced the new edge-ingress chart yet** (it shows `OutOfSync`), OR
2. It synced the StatefulSet/Deployment spec but the pods are stuck on the old ReplicaSet because of the CrashLoop wedge.

Let's find out exactly why the init container is crashing and whether the new spec is even present:

```bash
# 1. Why is the init container actually crashing? (the real error)
kubectl -n edge-ingress-system logs edge-ingress-58bcddf595-z2g78 -c geoip-downloader --previous --tail=40

# 2. Does the live Deployment spec have the NEW busybox bootstrap init, or still the old geoipupdate-only one?
kubectl -n edge-ingress-system get deploy etradie-edge-ingress \
  -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'

# 3. Is the GeoIP PVC from !146 actually created and bound?
kubectl -n edge-ingress-system get pvc
```

What each tells us:

- **Cmd 1** → the actual crash reason. If it's `HTTP 429 / too many requests` from MaxMind, that's the quota exhaustion — and the !146 fix is specifically designed so a cached DB lets the pod proceed *despite* 429. If the pod still hard-fails on 429, either there's no cached DB yet (cold start, quota still burned) or the new fault-tolerant logic isn't in this image.
- **Cmd 2** → if it lists only `geoip-downloader -> maxmindinc/geoipupdate:v6.0` and NOT a `geoip-bootstrap -> busybox:1.36` init, then **the !146 chart change is not in the rolled spec** — ArgoCD needs to sync edge-ingress. If it shows the busybox init, the fix is present and we're in the cold-start-no-cache window.
- **Cmd 3** → confirms the `geoip-data` PVC exists and is `Bound` (the persistence layer !146 added).

#### My read before you run them

Given the init image is still the old `geoipupdate:v6.0` and ArgoCD shows edge-ingress `OutOfSync`, my strong suspicion is **!146 hasn't been synced into edge-ingress yet** — the root-app sync earlier reconciled the Application *list* but edge-ingress's own resources may not have re-applied the new chart. If Cmd 2 confirms the old init, the fix is:

```bash
argocd app sync edge-ingress-staging --grpc-web --timeout 600
```

That re-applies `helm/edge-ingress` at GitHub `c97f4e21` (which has the PVC + busybox bootstrap init), then the new ReplicaSet rolls with the fault-tolerant init and the old CrashLooping one gets torn down.

**Run the three diagnostic commands and paste the output.** I want to see the actual crash reason (Cmd 1) and whether the new init container is in the spec (Cmd 2) before telling you to sync — so we fix the real cause, not guess.



DON'T WE NEED TO FORCE RE=PULL THE GHCR AND THEN MAKE THE ARGO TO REPEAT SO THAT EVERYTHING WILL BE FRESH?
softverse@Softverse:~/eTradie$ # 1. Why is the init container actually crashing? (the real error)
kubectl -n edge-ingress-system logs edge-ingress-58bcddf595-z2g78 -c geoip-downloader --previous --tail=40
2. Does the live Deployment spec have the NEW busybox bootstrap init, or still the old geoipupdate-only one?
kubectl -n edge-ingress-system get deploy etradie-edge-ingress   -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'
3. Is the GeoIP PVC from !146 actually created and bound?
kubectl -n edge-ingress-system get pvc
STATE: Running geoipupdate
Error retrieving updates: running the job processor: running job: getting update for GeoLite2-City: unexpected HTTP status code: received HTTP status code: 429: Daily GeoIP database download limit reached
Error from server (NotFound): deployments.apps "etradie-edge-ingress" not found
NAME                       STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
edge-ingress-geoip-cache   Pending                                                                      16m
softverse@Softverse:~/eTradie$
BEFORE WE CONTINUE, I WANT YOU TO DO SOMETHING IMPORTANT
I WANT YPU TO CREATE A FILE AT THE /DOCS/RUNBOOKS/ AND DOCUMENT EXACTLY ALL THIS WE DID ABOUT THE STAGING/PRODUCTION CHURN SO THAT IF THIS SESSION ENDS ANY MOMENT FROM NOW ANY OPERATOR OR WE IN THE NEXT SESSION WILL KNOW EXACTLY WHAT HAS HAPPENED, WHAT WE DID, THE ACTION TAKEN AND THE PLACE TO TAKE OFF TO CONTINUE TO STAY ALIGNED , CONSISTENT WITHOUT ANY CONFUSION OR BREAKING ANYTHING AGAIN
THIS IS VERY IMPORTANT
MAKE SURE IT'S CLEAR AND ACCURATE


Before I write the doc, two findings from your diagnostics that the checkpoint MUST capture accurately — because they change the "where to take off" instructions:

#### Critical finding 1 — the PVC is `Pending`, not Bound

```
edge-ingress-geoip-cache   Pending   ...   16m
```

The !146 GeoIP PVC was created but is **`Pending` (unbound)**. On K3s `local-path` with `WaitForFirstConsumer`, a PVC stays Pending until a pod actually mounts it and gets scheduled. The pod can't mount it because the init container CrashLoops before the volume binds in a Ready pod — and the PVC name here is `edge-ingress-geoip-cache`, which may not match what the chart's deployment expects to mount (the chart added `geoip-pvc.yaml`). This needs checking, but the key point: **the persistence layer isn't active yet.**

#### Critical finding 2 — the init is STILL the old `geoipupdate` doing a hard download, and it's hitting 429

```
STATE: Running geoipupdate
Error ...: HTTP status code: 429: Daily GeoIP database download limit reached
```

This is the **old** behavior !146 was meant to eliminate. The fault-tolerant busybox bootstrap (skip-if-cached, warn-and-proceed on 429) is **not in the running spec**. And the `etradie-edge-ingress` deployment name wasn't found — meaning the live resource is named differently than I queried, so I can't yet confirm whether ArgoCD synced the new chart.

#### Answering your question — do we force re-pull GHCR + re-sync?

**Partly, but GHCR is not the issue here.** The edge-ingress *application image* isn't the problem — the `geoip-downloader` is a separate public MaxMind image (`maxmindinc/geoipupdate:v6.0`), and the 429 is a MaxMind **server-side daily quota**, not a stale cached image. Force-pulling GHCR won't fix a 429. What's needed:
1. **Sync edge-ingress** so the new chart (busybox fault-tolerant init + correctly-wired PVC) actually rolls — this is the real fix.
2. **The MaxMind quota must reset (00:00 UTC)** before even the new init can do a true cold-start download. With the fix in place + a cached DB on the bound PVC, future restarts won't re-download.

So this is **not fully resolved tonight** — it's blocked on the quota reset, exactly as the !146 design anticipated. That's important to document honestly.

Let me write the checkpoint now, capturing all of this accurately.


Checkpoint created and committed to GitLab `main`: **`docs/runbooks/STAGING-PRODUCTION-CHURN-CHECKPOINT.md`**.

#### What the checkpoint captures (accurately, no guessing)

- **Root cause** — the `children/` recurse creating both `*-staging` + `*-production` on one box, shared releaseName/namespace, the field-manager fight, and the explicit link to *why it burned the MaxMind quota*.
- **The three-part fix** — !146 (GeoIP persistence), !147 (parking 11 apps to `environments/production/`), and the doc-consistency commit, with exact commit SHAs.
- **Git state** — GitHub canonical, GitLab mirror, the load-bearing push rule.
- **The live prune** — including the ownership verification (`engine-staging` is the canonical label owner; single shared `argocd-controller` field-manager) and the finalizer-stripped delete loop that was proven safe, plus the verified result (11 gone, staging pods unchanged at 106–107m age).
- **The ONE open item** — edge-ingress GeoIP, documented honestly with the verified facts: old `geoipupdate:v6.0` init still hitting 429, PVC `Pending`, two wedged ReplicaSets, and that this is **not** the prune's fault and **not** a GHCR problem.
- **Take-off-here steps** — the exact ordered commands for the next session, plus an explicit "What NOT to do" list (don't force-pull GHCR for a 429, don't loop delete/recreate, don't move production files back).

#### Answering your GHCR question directly

**No — force re-pulling GHCR will not help here, and re-syncing Argo blindly isn't the move yet.** The thing blocking edge-ingress is a **MaxMind server-side 429** (their daily download cap), and the init container hitting it is still the **OLD `geoipupdate:v6.0`** — meaning the !146 fault-tolerant busybox init **hasn't actually rolled into the live pod yet**. GHCR holds your *application* images; the GeoIP image is MaxMind's public Docker Hub image, and no amount of re-pulling changes a 429.

The correct sequence (now documented in the checkpoint) is:
1. Confirm the real edge-ingress workload name and whether the busybox bootstrap init is in the live spec (the `etradie-edge-ingress` name wasn't found, so we must check the actual name).
2. If the old init is still there → `argocd app sync edge-ingress-staging` to roll the !146 chart in.
3. **Then wait for 00:00 UTC** so the quota resets and the cold-start download succeeds **once** onto the now-bindable PVC. After that, the cache makes restarts immune to 429.

So edge-ingress is genuinely **quota-blocked tonight** — that's expected and by design, not a regression.

Want me to walk through Step 1 (find the real edge-ingress deployment name and check its init containers) now, so we know whether you need the `argocd app sync edge-ingress-staging` before the quota resets?



**Critical finding: the chart on `main` IS the !146 fix, but the init container's name is still `geoip-downloader` AND its image is `{{ .Values.geoip.bootstrapInitImage }}` (busybox).** The live pod you saw was running `maxmindinc/geoipupdate:v6.0` under the name `geoip-downloader` — so the live pod is on the **OLD** chart. The new chart keeps the same container *name* but changes the *image* to busybox and the logic to cache-aware.

This is the key: same name, different image + logic. So when you check the live spec, look at the **image**, not the name. If the live init image is `maxmindinc/geoipupdate:v6.0`, it's the old chart and needs syncing. If it's `busybox:1.36`, the new chart already rolled.

From your earlier diagnostic, the live init was `maxmindinc/geoipupdate:v6.0` → **old chart, not yet synced.** That confirms Step 2 (`argocd app sync edge-ingress-staging`) is needed.

Let me read the rest of the deployment template to confirm the cold-start hard-fail logic and the PVC mount, so I can tell you exactly what to expect after the sync + quota reset.


Real workload name (the chart uses edge-ingress.fullname; earlier "etradie-edge-ingress" 404'd)
kubectl -n edge-ingress-system get deploy
Inspect the live init container image (look at IMAGE, not name)
DEPLOY=$(kubectl -n edge-ingress-system get deploy -o name | grep -i edge-ingress | head -1)
kubectl -n edge-ingress-system get "$DEPLOY"   -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'
NAME           READY   UP-TO-DATE   AVAILABLE   AGE
cloudflared    1/1     1            1           119m
edge-ingress   0/1     1            0           119m
geoip-downloader  ->  maxmindinc/geoipupdate:v6.0
aop-ca-preflight  ->  alpine/openssl@sha256:923270611179f81b420bfb5bb5c18bf07fd59d84ed4163ac04cb371faa6d150f
softverse@Softverse:~/eTradie$



Confirmed. The diagnosis is now 100% certain.

#### What this proves

- **Real deployment name = `edge-ingress`** (not `etradie-edge-ingress` — that's why my earlier query 404'd).
- **The live init container is `geoip-downloader -> maxmindinc/geoipupdate:v6.0`** — that is the **OLD chart**. The !146 fix (which I just read on `main`) keeps the name `geoip-downloader` but changes the image to **`busybox:1.36`** with the cache-aware skip/warn/fail logic. The live pod is `maxmindinc/geoipupdate:v6.0`, so **the !146 chart has NOT rolled into edge-ingress yet.**

This is exactly the situation the checkpoint predicted: the fix is on GitHub `main`, but ArgoCD hasn't applied it to the edge-ingress workload's pod spec. The fix.

#### The sync — roll the !146 chart into edge-ingress

```bash
argocd app sync edge-ingress-staging --grpc-web --timeout 600
```

Then immediately re-check the init image to confirm the new spec landed:

```bash
DEPLOY=$(kubectl -n edge-ingress-system get deploy -o name | grep -i edge-ingress | head -1)
kubectl -n edge-ingress-system get "$DEPLOY" \
  -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'
```

**Expected after sync:** `geoip-downloader -> busybox:1.36` (plus `aop-ca-preflight -> alpine/openssl`). That confirms the fault-tolerant init is now in the spec.

#### What happens next — and the honest truth about tonight

I read the full init logic. Here's exactly how it behaves on a cold start (no cached `.mmdb` on the PVC, which is your case — the PVC is `Pending`/empty):

```
no cached DB -> attempt download -> MaxMind returns 429 (quota exhausted)
-> download fails -> check for cached DB -> none exists
-> exit 1 (FATAL: no usable GeoIP DB and download failed)
```

So **even with the new busybox init, the pod will STILL CrashLoop tonight** — because it's a true cold start (empty PVC) AND the quota is exhausted. The fault-tolerance only helps when a cached DB *already exists*. Right now there's no cache and no quota. The fix's hard-fail message even says this explicitly:

> `FATAL: no usable GeoIP DB and download failed. The MaxMind daily download cap may be exhausted (resets 00:00 UTC)`

#### So the realistic plan

1. **Sync now** so the new fault-tolerant init + PVC wiring are in the spec (do this tonight — no reason to wait).
2. **After 00:00 UTC** (quota reset), the next init attempt downloads the DB once, writes it to the PVC, the PVC binds, and edge-ingress reaches Ready.
3. From then on, every restart sees the cached DB and **skips the download entirely** — the 429 failure mode is permanently gone.

You could also short-circuit the wait if you want edge-ingress up *tonight*: manually seed the `.mmdb` onto the PVC (download it on your workstation from a non-rate-limited source / your MaxMind account web download, then `kubectl cp` it into a throwaway pod mounting the PVC). But that's optional and fiddly — the clean path is just to sync now and let the 00:00 UTC reset do the cold-start download.

Run the `argocd app sync edge-ingress-staging` + the re-check, and paste the output. Once I confirm the init image flipped to `busybox:1.36`, the fix is correctly in place and edge-ingress is simply waiting on the quota reset — which I'll note in the checkpoint so the next session knows it's expected.





DEPLOY=$(kubectl -n edge-ingress-system get deploy -o name | grep -i edge-ingress | head -1)
kubectl -n edge-ingress-system get "$DEPLOY" \
  -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'



IT SEEMS IT'S STUCK HERE:
 600
FATA[0004] rpc error: code = FailedPrecondition desc = another operation is already in progress
softverse@Softverse:/eTradie$
softverse@Softverse:/eTradie$
softverse@Softverse:/eTradie$ argocd app terminate-op edge-ingress-staging --grpc-web
Application 'edge-ingress-staging' operation terminating
softverse@Softverse:/eTradie$ argocd app sync edge-ingress-staging --grpc-web --timeout 600
TIMESTAMP                  GROUP                        KIND              NAMESPACE                           NAME           STATUS    HEALTH            HOOK  MESSAGE
2026-06-17T18:56:01+01:00                         ServiceAccount         edge-ingress-system           cloudflared           Synced2026-06-17T18:56:01+01:00  monitoring.coreos.com  ServiceMonitor         edge-ingress-system          edge-ingress           Synced2026-06-17T18:56:01+01:00  networking.k8s.io      NetworkPolicy          edge-ingress-system          edge-ingress           Synced2026-06-17T18:56:01+01:00  scheduling.k8s.io      PriorityClass                               edge-ingress-critical          Synced2026-06-17T18:56:01+01:00                          Namespace             edge-ingress-system   edge-ingress-system          Running    Synced                  namespace/edge-ingress-system serverside-applied
2026-06-17T18:56:01+01:00  external-secrets.io    ExternalSecret         edge-ingress-system      edge-ingress-tls         OutOfSync  Healthy                  externalsecret.external-secrets.io/edge-ingress-tls serverside-applied
2026-06-17T18:56:01+01:00                         ResourceQuota          edge-ingress-system  edge-ingress-resource-quota    Synced2026-06-17T18:56:01+01:00   apps                  Deployment             edge-ingress-system          edge-ingress         OutOfSync  Degraded                 Deployment.apps "edge-ingress" is invalid: [spec.template.spec.volumes[4].persistentVolumeClaim: Forbidden: may not specify more than 1 volume type, spec.template.spec.containers[0].volumeMounts[5].name: Not found: "geoip-data", spec.template.spec.initContainers[0].volumeMounts[0].name: Not found: "geoip-data"]
2026-06-17T18:56:01+01:00  external-secrets.io    ExternalSecret         edge-ingress-system  cloudflared-tunnel-token     OutOfSync  Healthy                  externalsecret.external-secrets.io/cloudflared-tunnel-token serverside-applied
2026-06-17T18:56:01+01:00                          Namespace                                   edge-ingress-system           Synced2026-06-17T18:56:01+01:00  batch                     CronJob             edge-ingress-system  edge-ingress-geoip-refresh     Synced2026-06-17T18:56:01+01:00  monitoring.coreos.com  ServiceMonitor         edge-ingress-system           cloudflared           Synced2026-06-17T18:56:01+01:00  external-secrets.io    ExternalSecret         edge-ingress-system   edge-ingress-aop-ca         OutOfSync  Healthy                  externalsecret.external-secrets.io/edge-ingress-aop-ca serverside-applied
2026-06-17T18:56:01+01:00  scheduling.k8s.io      PriorityClass          edge-ingress-system  edge-ingress-critical         Running    Synced                  priorityclass.scheduling.k8s.io/edge-ingress-critical serverside-applied
2026-06-17T18:56:01+01:00  external-secrets.io    ExternalSecret         edge-ingress-system  edge-ingress-maxmind         OutOfSync  Healthy                  externalsecret.external-secrets.io/edge-ingress-maxmind serverside-applied
2026-06-17T18:56:01+01:00                            Service             edge-ingress-system          edge-ingress           Synced   Healthy2026-06-17T18:56:01+01:00                            Service             edge-ingress-system  edge-ingress-metrics           Synced   Healthy2026-06-17T18:56:01+01:00                         ServiceAccount         edge-ingress-system          edge-ingress           Synced2026-06-17T18:56:01+01:00   apps                  Deployment             edge-ingress-system           cloudflared           Synced   Healthy2026-06-17T18:56:01+01:00  networking.k8s.io      NetworkPolicy          edge-ingress-system  cloudflared-network-policy     Synced2026-06-17T18:56:01+01:00                          ConfigMap             edge-ingress-system   edge-ingress-config           Synced2026-06-17T18:56:01+01:00                         PersistentVolumeClaim  edge-ingress-system  edge-ingress-geoip-cache       Synced   Progressing
2026-06-17T18:56:01+01:00                            Service             edge-ingress-system   cloudflared-metrics           Synced   Healthy


**Stop — this is a real chart bug, not a transient.** The sync surfaced a genuine validation error that explains everything. Read this line carefully:

```
Deployment.apps "edge-ingress" is invalid:
  [spec.template.spec.volumes[4].persistentVolumeClaim: Forbidden: may not specify more than 1 volume type,
   spec.template.spec.containers[0].volumeMounts[5].name: Not found: "geoip-data",
   spec.template.spec.initContainers[0].volumeMounts[0].name: Not found: "geoip-data"]
```

#### What this means

The !146 chart has a **defect in the `volumes:` section** of `deployment.yaml`:

1. **`volumes[4]` specifies more than one volume type in a single entry.** A volume entry can have exactly one source (e.g. `persistentVolumeClaim` OR `emptyDir`, not both). The `geoip-data` volume entry has been rendered with two sources at once — almost certainly a templating mistake where the PVC source and an emptyDir source (or similar) both ended up under the same volume name.
2. Because that volume entry is **rejected**, the volume named `geoip-data` is effectively not created → the init container's `volumeMounts[0].name: geoip-data` and the main container's `volumeMounts[5].name: geoip-data` both fail with `Not found: "geoip-data"`.

So the Deployment **cannot be applied** — that's why edge-ingress is stuck on the OLD ReplicaSet (the new spec is invalid and rejected by the API server). This is NOT the MaxMind 429 anymore; **the !146 chart itself won't apply.** The 429 is downstream of this; we never even get to a valid pod.

#### I need to see the volumes block to fix it correctly

The bug is in the `volumes:` section of `helm/edg
e-ingress/templates/deployment.yaml` (the part I haven't read yet — lines 240+). Let me read it.



Found the exact bug. The template is **correct** — so the problem is the **value**, not the template.

#### Root cause

The `geoip-data` volume renders conditionally:

```yaml
- name: geoip-data
  {{- if .Values.geoip.persistence.enabled }}
  persistentVolumeClaim:
    claimName: ...-geoip-cache
  {{- else }}
  emptyDir:
    sizeLimit: ...
  {{- end }}
```

The API error was `volumes[4].persistentVolumeClaim: Forbidden: may not specify more than 1 volume type`. That happens when the rendered volume ends up with **both** `persistentVolumeClaim` AND `emptyDir`. The only way this template produces both is **server-side-apply field-manager merging**: the OLD ReplicaSet's spec had `geoip-data` as an `emptyDir`, and the new sync applied `persistentVolumeClaim` on top — and because the existing `emptyDir` field wasn't owned/removed by the same manager, the merged object now carries **both** sources. That's why it's `volumes[4]` with two types, and why the mounts can't resolve.

Notice the live PVC is named `edge-ingress-geoip-cache` and the chart claims `{{ include "edge-ingress.fullname" . }}-geoip-cache` → `edge-ingress-geoip-cache`. **The names match.** And the PVC line in the sync output shows `Synced / Progressing`. So the PVC and CronJob applied fine — only the **Deployment** is wedged by the dual-volume-source merge conflict.

#### The fix — force a clean replace of the Deployment

ServerSideApply merging is the culprit, so a normal sync keeps merging into the broken object. The clean fix is to make ArgoCD **replace** the Deployment (recreate it from the chart spec, not 3-way-merge), or delete the broken Deployment so ArgoCD recreates it cleanly. Two options:

**Option A — targeted replace via ArgoCD (preferred, GitOps-native):**

```bash
argocd app sync edge-ingress-staging --grpc-web --timeout 600 \
  --resource apps:Deployment:edge-ingress \
  --replace
```

`--replace` makes ArgoCD do a `kubectl replace` (full overwrite) on the Deployment instead of an apply-merge, so the stale `emptyDir` field is dropped and only the chart's `persistentVolumeClaim` source remains.

**Option B — delete the broken Deployment, let ArgoCD recreate it:**

```bash
kubectl -n edge-ingress-system delete deploy edge-ingress
argocd app sync edge-ingress-staging --grpc-web --timeout 600
```

This is safe — edge-ingress isn't serving (it's been 0/1 CrashLoop the whole time), so deleting the Deployment loses nothing. ArgoCD recreates it fresh from the chart with the single correct volume source.

**I recommend Option A** (`--replace` scoped to the Deployment) — it's the least destructive and stays inside ArgoCD's reconcile model.

#### After the replace — verify the volume is now single-source

```bash
DEPLOY=$(kubectl -n edge-ingress-system get deploy -o name | grep -i edge-ingress | head -1)
# Init image should now be busybox:
kubectl -n edge-ingress-system get "$DEPLOY" \
  -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'
# The geoip-data volume should show ONLY persistentVolumeClaim:
kubectl -n edge-ingress-system get "$DEPLOY" \
  -o jsonpath='{range .spec.template.spec.volumes[*]}{.name}{": "}{.persistentVolumeClaim.claimName}{.emptyDir}{"\n"}{end}'
```

Expected:
- init: `geoip-downloader -> busybox:1.36`
- volume line: `geoip-data: edge-ingress-geoip-cache` (a PVC claim name, and NOT also showing an emptyDir)

#### Then the honest end-state for tonight

Once the Deployment is valid and rolls:
- The new busybox init runs. **Cold start + quota still exhausted → it will hard-fail `exit 1`** (no cached DB yet), so the pod stays Init-CrashLoop **until 00:00 UTC**. That's expected and correct — the chart is now right; it's just waiting on the quota.
- After 00:00 UTC, the init downloads once → PVC binds → edge-ingress goes Ready → cached forever after.

Run **Option A**, paste the two verification outputs. Once the `geoip-data` volume shows a single PVC source and the init is busybox, the chart defect is resolved and edge-ingress is correctly parked waiting for the quota reset. I'll update the checkpoint with this finding (the dual-volume SSA merge bug + the `--replace` fix) so the next session has it.