# MT5 Multi-Broker Provisioning — Engineering Implementation Runbook

**Exoper Platform — Broker-Agnostic MT5 Account Provisioning**
Prepared for: Engineering Team
**Status: AUTHORITATIVE. This is the single source of truth for the
multi-broker implementation. Operators and engineers MUST follow this
document top-to-bottom and stay strictly aligned with it. If reality
diverges from this document, STOP and update this document first — do
not improvise a parallel design.**

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [What Does Not Work (Ruled Out)](#2-what-does-not-work-ruled-out)
3. [The Correct Architecture](#3-the-correct-architecture)
4. [The Broker → Entity → Server Hierarchy](#4-the-broker--entity--server-hierarchy)
5. [The Broker Registry — Schema + Storage](#5-the-broker-registry--schema--storage)
6. [Operator Runbook — Acquire, Bake, Verify, Publish (per broker)](#6-operator-runbook--acquire-bake-verify-publish-per-broker)
7. [Engineering Implementation — Exact File-by-File Change Set](#7-engineering-implementation--exact-file-by-file-change-set)
8. [Runtime Flow — End to End (per tenant)](#8-runtime-flow--end-to-end-per-tenant)
9. [Dashboard UI — Find Broker → Entity → Server Wizard](#9-dashboard-ui--find-broker--entity--server-wizard)
10. [Ordered Execution Plan (do these in this order)](#10-ordered-execution-plan-do-these-in-this-order)
11. [Summary: Problem vs Solution](#11-summary-problem-vs-solution)
12. [Why This Is the Industry-Standard Approach](#12-why-this-is-the-industry-standard-approach)
13. [Glossary of Authoritative Paths + Names](#13-glossary-of-authoritative-paths--names)

---

## 1. The Problem

### 1.1 What We Are Trying to Do

Exoper provisions a containerized MT5 terminal per tenant (StatefulSet,
Service, ServiceAccount, PVC, Vault credentials) so that each user can
run automated analysis and trading on their own broker account. The
platform is explicitly designed to be broker-agnostic: users connect
whichever broker they already trade with.

### 1.2 What Is Confirmed Working

The following is provisioned, tested, and functioning correctly:

- Tenant pod creation: StatefulSet, Service, ServiceAccount, PVC, Vault
  credentials (engine `HostedProvisioner`).
- The mt-node container image runs; Wine and Xvfb start cleanly.
- The MT5 terminal binary launches and compiles inside the Wine prefix
  (defect #13 fixed via the pre-installed portable zip).
- `libzmq.dll` and all EA dependencies are present and load correctly
  (defect #14 fixed; baked into the image with build-time assertions).
- The LiveUpdate self-restart loop is fixed (defect #15a).
- `startup.ini` is generated with the correct Login, Password, and
  Server fields, and the `/config:` flag is honored by the terminal at
  launch.

### 1.3 The Single Remaining Blocker

MT5 never logs in to the broker. Diagnosis confirms:

- No network line indicating a successful server handshake in the
  terminal journal (the journal ends after `0 file(s) compiled`).
- Zero Deriv-related entries in the pod's `servers.dat` — confirmed via
  direct binary inspection (28,544 bytes, entirely populated by other,
  unrelated brokers).
- `Server=Deriv-Demo` in `startup.ini` has no effect because the
  terminal has no record of what host/port that name resolves to, and
  `bases/` + `profiles/` are never created (proof MT5 never logged in).

### 1.4 Root Cause

`servers.dat` is not a manually editable broker list. It is populated in
exactly two ways:

1. Through a live network discovery handshake against MetaQuotes'
   central broker directory, triggered ONLY by the terminal GUI's
   "Open an Account" / "Find Broker" flow. Headless `startup.ini` does
   NOT trigger this path, and even when triggered it is unreliable
   inside containerized/headless environments.
2. Through a broker's own branded MT5 installer, which pre-seeds
   `servers.dat` with that specific broker's server entries at install
   time.

Our current image was produced from the generic MetaQuotes installer,
whose `servers.dat` only contains MetaQuotes' own demo servers plus a
small fixed set of major brokers. Deriv — and the majority of brokers
our users bring — are not in that default list, and the headless
runtime flow never populates them.

### 1.5 Why This Is Harder Than a Single-Broker Fix

The platform must support an unknown, growing set of brokers. At 200
users we can reasonably expect 20+ distinct brokers in use. This rules
out any solution that assumes a single broker, and it rules out any
solution that depends on a runtime mechanism we cannot reliably control
inside our container network (the same discovery handshake that is
already failing for Deriv).

---

## 2. What Does Not Work (Ruled Out)

This section exists so the team does not re-investigate dead ends.

### 2.1 Manually Editing servers.dat

`servers.dat` is a proprietary binary format, generated and consumed
only by the MT5 terminal itself. It is not intended to be hand-edited or
templated by third-party tooling. There is no supported, documented way
to inject arbitrary broker entries into it directly. **We therefore
never WRITE `servers.dat`; we only ever produce it via the broker's own
installer and then READ it back to extract the authoritative server
list (§6).**

### 2.2 IP:Port Direct Connection as a Universal Bypass

MetaQuotes' documentation confirms the `Server=` field accepts a literal
`address:port`, bypassing the named-server lookup. This is real and
documented, but:

- It only resolves the named-server lookup — it does not guarantee the
  broker's server cluster accepts the connection, since trade servers
  commonly use TLS/certificate handshakes and load-balanced clusters
  tied to broker-specific configuration.
- No production multi-broker system researched uses this as a
  general-purpose mechanism.
- **Conclusion:** not a verified, scalable solution across an arbitrary
  set of brokers. Do not rely on it as the core mechanism. (It remains
  useful only as a one-off DIAGNOSTIC to distinguish name-resolution
  failure from network-level failure on a single broker.)

### 2.3 Relying on Runtime Broker Discovery Inside the Container

This is the mechanism already failing for Deriv. Headless `startup.ini`
does not even initiate it, and where it can be initiated it is unreliable
inside containerized/headless environments. **Opening egress to
MetaQuotes' broker-directory endpoints does NOT fix this**, because the
headless launch path never drives discovery. This cannot be the basis of
a dependable multi-tenant platform.

### 2.4 Running the Branded Installer Inside the Pod / CI (defect #13)

Running `wine <broker>setup.exe /auto` inside `docker build` or inside
the tenant pod's init under `xvfb-run` HANGS INDEFINITELY — the GUI
web-installer waits on a prompt nobody clicks. This is the documented
defect #13 in `docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md`. It is
why the current generic terminal is shipped as a PRE-INSTALLED PORTABLE
ZIP, not installed at build time. **The same rule applies to every
broker: the installer is run ONCE on an interactive Wine+Xvfb
workstation, never in CI and never in the pod.**

---

## 3. The Correct Architecture

### 3.1 Core Principle

> **Broker-agnostic at the platform/orchestration layer.
> Broker-specific at the installer layer.
> The broker-specific bake happens ONCE per broker on a workstation;
> the result is a signed, sha-pinned portable artifact in R2; tenants
> get it layered in at provisioning time. The mt-node image itself
> stays broker-agnostic and unchanged.**

There is no mechanism — documented or undocumented — that makes a single
generic MT5 binary work uniformly across arbitrary brokers without
broker-specific setup. Every real multi-broker system installs each
broker's own build and orchestrates around that constraint.

### 3.2 High-Level Model

```
  (ONE-TIME, PER BROKER, ON AN INTERACTIVE WINE+XVFB WORKSTATION)
  ┌──────────────────────────────────────────────┐
  │ 1. Download branded installer from broker's official channel        │
  │    (acquisition only; compute SHA256 immediately)                   │
  │ 2. Run installer to completion under interactive Wine+Xvfb          │
  │ 3. Verify servers.dat populated: strings servers.dat | grep broker  │
  │ 4. Capture the EXACT server strings from servers.dat (the truth)    │
  │ 5. Zip the resulting 'MetaTrader 5/' dir -> <brand>-portable.zip    │
  │ 6. Compute SHA256 of the zip                                        │
  └──────────────────────────────────────────┬───────┘
                                                       │
                                                       ▼
  ┌───────────────────────────────────────────────┐
  │   CLOUDFLARE R2  (system source of truth; sha-pinned)               │
  │   r2://etradie-installers/                                          │
  │     ├─ mt5-portable.zip            (generic; unchanged)              │
  │     ├─ mt4-portable.zip            (generic; unchanged)              │
  │     └─ broker-bundles/                                              │
  │          ├─ deriv-portable.zip   + deriv-portable.zip.sha256        │
  │          ├─ exness-portable.zip  + exness-portable.zip.sha256       │
  │          └─ ...                  (one per supported brand)           │
  └───────────────────────────────────────────────┬┘
                                                                       │
  (RUNTIME, PER TENANT)                                                │
      User: Find Broker → Entity → Server (dropdown)  ... §9          │
                          │                                            │
                          ▼                                            │
      Engine HostedProvisioner resolves broker_id + entity_id          │
      via the Broker Registry → the brand's R2 bundle + sha            │
                          │                                            │
                          ▼                                            │
      StatefulSet gains an initContainer that:                         │
        - downloads <brand>-portable.zip from R2  <──────────────────┘
        - verifies SHA256 against the Registry pin
        - unpacks it into a shared volume (broker-bundle)
                          │
                          ▼
      entrypoint.sh installs the bundle's servers.dat into
      $MT_DIR/config/ BEFORE launching terminal64.exe
                          │
                          ▼
      MT5 resolves Server=<name> locally → logs in → symbols →
      chart → EA attaches → :5555 binds → pod 3/3 Ready
```

### 3.3 Why The Bake Is On A Workstation, Not In CI/Pod

See §2.4. The branded installer is an interactive GUI web-installer that
hangs under headless xvfb. The bake is therefore a deliberate, one-time
human+workstation operation per broker (§6). Its OUTPUT (the portable
zip) is what enters the automated supply chain — identical posture to
the existing generic `mt5-portable.zip`.

### 3.4 Acquisition URL vs System Fetch Path (critical distinction)

- **Acquisition URL** (e.g. `https://download.mql5.com/cdn/web/<broker>/mt5/<broker>5setup.exe`):
  used ONCE, BY A HUMAN, on the workstation, to obtain the installer.
  Our CI build guard BLOCKS the substring `download.mql5.com`, so this
  URL must NEVER appear as a pipeline/runtime fetch path.
- **System fetch path** (e.g. `r2://etradie-installers/broker-bundles/deriv-portable.zip`):
  the ONLY path the provisioner/initContainer ever fetches from. This
  is what the Broker Registry stores in `bundle_r2_path`.

### 3.5 Verification Gate

Before a broker entity is marked `active` in the Registry it MUST pass:

```bash
strings "<prefix>/drive_c/Program Files/MetaTrader 5/config/servers.dat" \
  | grep -i "<brand>"
# -> must return non-empty broker server entries
```

Same discipline already applied to the WineHQ version pin and the
`terminal64.exe`/`libzmq.dll` build-time assertions: confirm before
trusting, never assume.

### 3.6 Unsupported / Long-Tail Brokers

For brokers outside the actively maintained Registry, the platform
presents a clear, honest state rather than a silent failure:

- The wizard flags the broker as "not yet supported" and offers a
  request/waitlist action.
- Brokers that do not offer MT5 at all (e.g. eToro, Interactive Brokers,
  and possibly XTB depending on region) are recorded with
  `mt5_supported: false` so the wizard refuses them with a clear reason.
- Adding a broker is a bounded task: acquire installer → bake → verify
  → publish zip to R2 → add one Registry entry. No mt-node image rebuild,
  no per-broker engineering.

---

## 4. The Broker → Entity → Server Hierarchy

A brand is NOT one flat record. It is a parent over one or more **legal
entities**, each regulated separately and each with its OWN server list.
The entity is what determines which servers appear in the user's
dropdown and (where a brand ships per-entity installers) which installer
is authoritative.

```
Brand (e.g. "Exness")
 ├─ Entity: Exness Technologies Ltd     (regulator: FSA Seychelles)
 │    ├─ demo servers: [Exness-MT5Trial9, Exness-MT5Trial10, ...]
 │    └─ live servers: [Exness-Real, Exness-Real2, ...]
 ├─ Entity: Exness (SC) Ltd            (regulator: ...)
 │    └─ ... own server list ...
 └─ ... more entities ...

Brand (e.g. "Deriv")
 └─ Entity: Deriv.com Limited
      ├─ demo servers: [Deriv-Demo]
      └─ live servers: [Deriv-Server, Deriv-Server-02, Deriv-Server-03]
```

Packaging note (decided at acquisition):
- Some brands ship ONE unified installer that seeds every entity's
  servers into a single `servers.dat`. Then all entities + servers fall
  out of one bake automatically.
- Some brands ship PER-ENTITY installers (the official download page
  forces an entity choice). Then each chosen installer is baked
  separately and produces that entity's servers.

We do NOT research server names from broker websites. We EXTRACT them
from the baked `servers.dat` (§6). The website is used only to obtain the
installer and to learn whether packaging is unified or per-entity.

v1 scope decision: for multi-entity brands, ship the PRIMARY entity
only (e.g. Exness → `Exness Technologies Ltd`) and backlog the rest;
add more entities later with the identical bake procedure.

---

## 5. The Broker Registry — Schema + Storage

### 5.1 Storage decision

The Registry is a **versioned config file in Git** (source of truth),
validated in CI against a JSON Schema, and loaded by the engine at boot.
It is NOT a per-tenant DB table. Per-tenant data continues to live in
`broker_connections`; the Registry is shared, reviewed-by-PR, and
changes rarely. Files:

```
infrastructure/broker-catalog/
  schema.json                 # JSON Schema; CI validates every entry
  deriv.yaml                  # one file per brand
  exness.yaml
  ...
```

### 5.2 Per-brand record schema (authoritative)

```yaml
brand_id: deriv                      # lowercase, underscore-separated
display_name: "Deriv"
official_website: https://deriv.com
mt5_supported: true
installer_packaging: per_entity      # unified | per_entity | none
status: active                       # active | pending_bake | unsupported_mt5 | inactive
entities:
  - entity_id: deriv_com_limited     # brand-prefixed, lowercase
    display_name: "Deriv.com Limited"
    regulator: "unknown"             # advisory, for the wizard only
    # ACQUISITION ONLY — human/workstation use; never a runtime fetch path:
    acquisition_url: "https://download.mql5.com/cdn/web/deriv.investments.ltd/mt5/deriv5setup.exe"
    # SYSTEM FETCH PATH — the only path the provisioner ever pulls:
    bundle_r2_path: "r2://etradie-installers/broker-bundles/deriv-portable.zip"
    bundle_sha256: "<sha256 of the zip, pinned after bake>"
    verified_on: "2026-06-21"        # date the verification gate passed
    servers:
      demo:
        - "Deriv-Demo"
      live:
        - "Deriv-Server"
        - "Deriv-Server-02"
        - "Deriv-Server-03"
```

Rules:
- `bundle_r2_path` + `bundle_sha256` are what the provisioner uses. They
  point at the BAKED ZIP, not the raw `.exe`.
- `servers.demo` / `servers.live` are EXACTLY the strings extracted from
  the baked `servers.dat` (§6 step 5), verbatim, every numbered variant.
- `status: active` is only permitted after the §3.5 verification gate
  passes and the zip + sha are uploaded to R2.
- `mt5_supported: false` brands carry `entities: []` and are surfaced as
  unsupported in the wizard.

---

## 6. Operator Runbook — Acquire, Bake, Verify, Publish (per broker)

Perform this ONCE per broker brand (or per entity for per-entity
packaging) on an INTERACTIVE Wine+Xvfb workstation. This is the same
flow that produced the existing generic `mt5-portable.zip`.

> Prerequisites on the workstation: Wine (matching the image's WineHQ
> pin where practical), Xvfb available, `unzip`/`zip`, `sha256sum`,
> `strings`. An interactive X session (or a working `xvfb-run` where the
> branded installer actually COMPLETES — confirm it does not hang).

### Step 1 — Acquire the installer (acquisition URL, human only)

```bash
# Deriv (single entity)
curl -L -o deriv5setup.exe \
  "https://download.mql5.com/cdn/web/deriv.investments.ltd/mt5/deriv5setup.exe"

# Exness (primary entity for v1)
curl -L -o exness5setup.exe \
  "https://download.mql5.com/cdn/web/exness.technologies.ltd/mt5/exness5setup.exe"
```

### Step 2 — Compute + record the installer SHA256 (security gate)

```bash
sha256sum deriv5setup.exe exness5setup.exe
```
The filename proves nothing (malware has shipped under the exact name
`exness5setup.exe`). Trust is established ONLY by the exact official
domain/path above + the SHA256 you compute here. Never source the
installer from a mirror/forum/backup link.

### Step 3 — Run the installer to completion (interactive Wine)

```bash
export WINEPREFIX=~/mt-bake/<brand>/wine
wine wineboot --init; wineserver --wait
# Run the branded installer. Use interactive X if xvfb-run hangs.
wine ./<brand>5setup.exe        # complete the install; cosmetic post-install
                                 # page-faults are fine if files landed.
wineserver --wait
```

### Step 4 — Verify servers.dat is populated (the §3.5 gate)

```bash
P="$WINEPREFIX/drive_c/Program Files/MetaTrader 5"
strings "$P/config/servers.dat" | grep -i deriv     # non-empty == pass
strings "$P/config/servers.dat" | grep -i exness    # non-empty == pass
```
If empty, the install did not seed the broker — STOP; do not publish.

### Step 5 — Capture the EXACT server strings (Registry truth)

Read the server names directly from the populated terminal. Either:
- `strings "$P/config/servers.dat" | grep -i <brand>` and record the
  server tokens verbatim, OR
- on the same interactive terminal: File → Open an Account → type the
  broker → step into each entity → cancel → File → Login to Trade
  Account → open the Server dropdown → record EVERY server string
  verbatim (including every numbered variant; do not assume a pattern).

These strings populate `servers.demo[]` / `servers.live[]` in the
Registry. Do not paraphrase or normalise capitalisation.

### Step 6 — Zip the portable directory

```bash
cd "$WINEPREFIX/drive_c/Program Files"
zip -rq /tmp/<brand>-portable.zip "MetaTrader 5"
sha256sum /tmp/<brand>-portable.zip   # record as bundle_sha256
```
The zip MUST have a top-level `MetaTrader 5/` directory (same layout the
existing generic zip uses, so the entrypoint's seed logic is unchanged).

### Step 7 — Publish to R2 (system source of truth)

Upload to the existing `etradie-installers` bucket under
`broker-bundles/`:
```
r2://etradie-installers/broker-bundles/<brand>-portable.zip
r2://etradie-installers/broker-bundles/<brand>-portable.zip.sha256
```

### Step 8 — Write/Update the Registry entry + open a PR

Fill `infrastructure/broker-catalog/<brand>.yaml` per §5.2 with
`bundle_r2_path`, `bundle_sha256`, the captured `servers.*`, `verified_on`,
and `status: active`. CI validates against `schema.json`. Merge.

Result: the broker is live for new provisions with zero image rebuild.

---

## 7. Engineering Implementation — Exact File-by-File Change Set

Grouped by area, in dependency order. "NEW" = create; "MODIFY" = edit.

### 7.1 Broker Registry (control plane)

- **NEW** `infrastructure/broker-catalog/schema.json` — JSON Schema for
  the §5.2 record. CI fails on any non-conforming entry.
- **NEW** `infrastructure/broker-catalog/deriv.yaml` — first seeded brand.
- **NEW** `infrastructure/broker-catalog/exness.yaml` — second seeded
  brand (primary entity only for v1).
- **NEW** `src/engine/ta/broker/registry.py` — loader + in-memory model:
  parses the catalog at engine boot, exposes
  `resolve(brand_id, entity_id) -> {bundle_r2_path, bundle_sha256,
  servers}` and `list_active()` for the API. Fail-closed if a
  referenced bundle/sha is missing.
- **NEW** `tests/engine/ta/broker/test_registry.py` — schema-load,
  resolution, and unsupported-broker tests.

### 7.2 Engine API (serve the registry to the dashboard)

- **MODIFY** `src/engine/routers/broker_connections.py`
  - Add `GET /api/broker/registry` returning active brands → entities
    → servers (demo/live), plus `mt5_supported` / `status` so the
    wizard can render "unsupported" states.
  - In `create_broker_connection` (the `hosted` branch): accept and
    validate `broker_id` + `entity_id`; resolve them via the Registry;
    if `mt5_server` is provided it MUST be a member of that entity's
    server list (else 422). Reject unsupported brokers at submit time
    (fail fast, not after a 5-minute pod cycle).
- **MODIFY** `src/engine/schemas.py` — `CreateBrokerConnectionRequest`
  gains `broker_id: str | None`, `entity_id: str | None`. Keep
  `mt5_server` (now validated against the registry; also the
  advanced-override path).

### 7.3 Persistence (record which broker/entity a row used)

- **MODIFY** `src/engine/processor/storage/schemas/broker_connection_schema.py`
  — add nullable columns `broker_id: str|None`, `broker_entity_id: str|None`.
- **MODIFY** `src/engine/processor/storage/repositories/broker_connection_repository.py`
  — persist/read the two new columns.
- **NEW** Alembic migration (next revision after 0033) under the
  project's migration dir — add the two columns, nullable, no backfill.

### 7.4 Provisioner (layer the bundle into the pod)

- **MODIFY** `src/engine/ta/broker/mt5/hosted/provisioner.py`
  - `provision_account(...)` accepts `broker_id`, `entity_id`.
  - Resolve the bundle via `registry.resolve(...)`.
  - In `_upsert_statefulset`, add an **initContainer** `broker-bundle`
    that: downloads `bundle_r2_path` (R2 only), verifies `bundle_sha256`,
    unzips into a shared `emptyDir` volume `broker-bundle` mounted at
    `/broker-bundle`. The mt-node container mounts the same volume
    read-only at `/broker-bundle`.
  - Stamp `etradie.io/broker-bundle-sha256` on the pod template so a
    registry bump triggers a controlled rolling restart (same mechanism
    as the existing credentials checksum).
  - Thread `MT_BROKER_ID` / `MT_BROKER_ENTITY_ID` env for observability
    (NOT load-bearing for login).
- **MODIFY** `src/engine/ta/broker/mt5/hosted/recovery.py` — pass
  `broker_id` + `entity_id` from the row into `provision_account` on
  reprovision (idempotent; no behavioural change otherwise).

### 7.5 Container entrypoint (install servers.dat before launch)

- **MODIFY** `docker/mt-node/entrypoint.sh`
  - Before the supervised launch loop, add an idempotent block:
    ```sh
    BROKER_BUNDLE_DIR="${BROKER_BUNDLE_DIR:-/broker-bundle}"
    if [ -f "$BROKER_BUNDLE_DIR/servers.dat" ]; then
      install -m 0644 "$BROKER_BUNDLE_DIR/servers.dat" "$MT_DIR/config/servers.dat"
      # plus any companion files the broker install wrote, if present:
      [ -d "$BROKER_BUNDLE_DIR/bases" ]   && cp -a "$BROKER_BUNDLE_DIR/bases/."   "$MT_DIR/bases/"   2>/dev/null || true
      log INFO "Installed broker servers.dat from $BROKER_BUNDLE_DIR"
    else
      log INFO "No broker bundle present; using image-baked servers.dat (dev/compose)"
    fi
    ```
  - Safe when the volume is absent (dev/docker-compose): logs and
    continues. No change to the LiveUpdate pin or launch line.
  - NOTE: the bundle's `servers.dat` is sourced from the broker's own
    install (§6), so this is the authoritative file — we INSTALL it, we
    never edit it.

> Alternative to the initContainer (§7.4): if the bundle is small enough,
> the whole broker portable zip can instead BE the seed (the entrypoint
> already seeds the Wine prefix from a template). For correctness and
> size, the chosen design layers ONLY `servers.dat` (+ companions) via
> the bundle volume and keeps the generic portable terminal as the base.
> Do not change this without updating this document.

### 7.6 Helm chart (keep chart-rendered == engine-rendered)

- **MODIFY** `helm/mt-node/templates/statefulset.yaml` — mirror the
  `broker-bundle` initContainer + `emptyDir` volume + read-only mount so
  the chart-rendered platform path and the engine-runtime path produce
  wire-identical pods (existing invariant).
- **MODIFY** `helm/mt-node/values.yaml` (+ `values-staging.yaml`,
  `values-production.yaml`) — add `brokerBundle.image` (the init image
  used to fetch+verify+unzip) and `brokerBundle.r2Path` / `.sha256`
  plumbing for the chart path.

### 7.7 Dashboard UI (Find Broker → Entity → Server)

- **NEW** `cotradee/src/features/broker/api/brokerRegistry.ts` — React
  Query hook over `GET /api/broker/registry`.
- **MODIFY** `cotradee/src/features/onboarding/components/steps/BrokerStep.tsx`
  — replace the free-text `mt5_server` input with the three-stage
  wizard (§9). Keep a hidden "Advanced" toggle exposing the original
  free-text field.
- **MODIFY** `cotradee/src/features/broker/api/brokerConnections.ts` —
  `useCreateBrokerConnection` payload gains `broker_id` + `entity_id`.
- **MODIFY** the broker-connections settings surface (the non-onboarding
  create/edit form, under `cotradee/src/features/settings/` or the
  broker feature) to use the same wizard component.

### 7.8 Docs cross-links

- **MODIFY** `docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md` — update
  the resume pointer to reference THIS document as the agreed fix for
  the login blocker (supersedes the #15b "startup.ini not honored"
  hypothesis with the confirmed root cause: missing broker in
  `servers.dat`).

---

## 8. Runtime Flow — End to End (per tenant)

1. User completes the wizard (§9): picks brand → entity → server, enters
   login + password. Dashboard POSTs `broker_id`, `entity_id`,
   `mt5_server`, `mt5_login`, `mt5_password`, `platform`,
   `connection_type=hosted`.
2. `broker_connections.py` validates `mt5_server` ∈ entity server list
   via the Registry (else 422, fail fast). Row is written with
   `broker_id` + `broker_entity_id`.
3. `HostedProvisioner.provision_account(broker_id, entity_id, ...)`
   resolves the brand's `bundle_r2_path` + `bundle_sha256`.
4. StatefulSet is created with the `broker-bundle` initContainer
   (download from R2 → verify sha → unzip to `/broker-bundle`) and the
   pod-template annotation `etradie.io/broker-bundle-sha256`.
5. Pod boots: Vault Agent renders creds → `entrypoint.sh` installs
   `/broker-bundle/servers.dat` into `$MT_DIR/config/servers.dat`
   (§7.5) BEFORE launch.
6. `entrypoint.sh` writes `startup.ini` (Login/Password/Server) and
   launches `wine terminal64.exe /config:startup.ini`.
7. MT5 resolves `Server=<name>` locally (now present in `servers.dat`)
   → logs in → downloads symbols → opens chart → EA attaches
   (`AllowDllImport=true` from `[Experts]`) → `libzmq.dll` resolves
   (already baked) → binds `:5555`.
8. startupProbe (`tcp :5555`) passes → watchdog `/healthz` reports
   `mt5_connected=1` + `authenticated=1` → pod 3/3 Ready.
9. Symbol two-boot proceeds as already designed (sentinel → resolve →
   patch `MT_SYMBOL` → one roll).

---

## 9. Dashboard UI — Find Broker → Entity → Server Wizard

Mirrors the native MT5 mobile "Find Broker" UX the users already know.

Stage 1 — Find Broker:
- Searchable dropdown over `GET /api/broker/registry` active brands.
- Brands with `mt5_supported: false` show a disabled "MT5 not offered by
  this broker" state. Unknown brokers show a "Request this broker" CTA.

Stage 2 — Select Entity:
- If the brand has one entity, auto-select and skip the visible step.
- If multiple, show the entity list (display_name + regulator).

Stage 3 — Select Server + Credentials:
- Server is a DROPDOWN populated from the chosen entity's
  `servers.demo[]` + `servers.live[]` (no free typing).
- Login (text) + Password (password) + connection name.

Advanced override (hidden by default):
- A toggle reveals the original free-text `mt5_server` input for power
  users / long-tail unblock. The submit still resolves a `broker_id`
  via the Registry; if no brand matches, the user gets a clear
  "broker not yet supported" message rather than a silent pod failure.

Form submit payload (hosted):
```json
{
  "connection_type": "hosted",
  "name": "...",
  "platform": "mt5",
  "broker_id": "deriv",
  "entity_id": "deriv_com_limited",
  "mt5_server": "Deriv-Demo",
  "mt5_login": "...",
  "mt5_password": "..."
}
```

---

## 10. Ordered Execution Plan (do these in this order)

**Phase 0 — Registry foundation (unblocks everything; do first).**
1. `infrastructure/broker-catalog/schema.json` (§7.1).
2. `src/engine/ta/broker/registry.py` loader + tests (§7.1).
3. Alembic migration + schema/repository columns (§7.3).

**Phase 1 — Bake + publish the first two brokers (operator, §6).**
4. Deriv: acquire → bake → verify → zip → R2 → `deriv.yaml`.
5. Exness (primary entity): same procedure → `exness.yaml`.
   (Code in Phase 2 can proceed in parallel once Deriv's zip is on R2.)

**Phase 2 — Engine wiring.**
6. `GET /api/broker/registry` + create-path validation (§7.2).
7. Provisioner initContainer + bundle resolution + annotation (§7.4).
8. `entrypoint.sh` servers.dat install block (§7.5).
9. Helm chart mirror (§7.6).

**Phase 3 — Dashboard wizard.**
10. Registry API hook + BrokerStep wizard + settings form + payload
    fields (§7.7).

**Phase 4 — End-to-end + rollout.**
11. Re-provision Deriv FROM THE DASHBOARD; verify the §8 chain to 3/3
    Ready; confirm `servers.dat` contains Deriv via the §3.5 gate on the
    live pod.
12. Repeat for Exness; mark both `active`.
13. Onboard the next most-requested brokers by repeating Phase 1 only.
14. Update `docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md` resume
    pointer (§7.8).

**Ongoing — operational.**
- Re-verify each broker's bundle on a cadence (brokers rotate servers;
  pinned zips go stale). Re-bake → re-verify → bump `bundle_sha256` →
  rolling restart picks it up (or the recovery sweep does).
- Registry entries that fail re-verification are set `status: inactive`;
  the wizard reflects that to affected users.

---

## 11. Summary: Problem vs Solution

| Layer | Current State | Target State |
|---|---|---|
| **Installer** | Generic MetaQuotes portable zip | Broker-specific portable bundle, baked once per broker on a workstation |
| **Server discovery** | Headless runtime handshake (never triggered / unreliable; currently failing) | Pre-seeded `servers.dat` from the broker's own install, layered in per tenant — zero runtime discovery |
| **Broker mapping** | None | Broker Registry in Git — schema-validated, brand→entity→server, one file per brand |
| **Installer source** | n/a | Acquisition via broker official URL (human, one-time); SYSTEM fetch via R2 only, sha-pinned |
| **Where install runs** | (generic) workstation bake | Per-broker workstation bake (NEVER in CI/pod — defect #13) |
| **Pod composition** | Single broker-agnostic image | Same image + per-tenant `broker-bundle` initContainer layering `servers.dat` |
| **UI** | Free-text server field | Find Broker → Entity → Server dropdown (advanced free-text override hidden) |
| **Scaling to N brokers** | Not solved | Linear, bounded: one bake + one Registry file per broker, reused by all tenants on that broker |

---

## 12. Why This Is the Industry-Standard Approach

Broker-specific binaries, centrally maintained and selected dynamically
per tenant by an orchestration layer, is the consistent model across
every MT5 hosting, white-label, and multi-broker VPS provider examined.
None make a single generic MT5 binary broker-agnostic at runtime; all
install each broker's own build once and orchestrate around that
constraint. Exoper's broker-agnostic promise is delivered correctly at
the orchestration layer (full engineering control) rather than at the
MT5 binary layer (no such control exists).

---

## 13. Glossary of Authoritative Paths + Names

| Thing | Value |
|---|---|
| R2 bucket | `etradie-installers` |
| Generic MT5 zip (unchanged) | `r2://etradie-installers/mt5-portable.zip` |
| Per-broker bundles dir | `r2://etradie-installers/broker-bundles/` |
| Bundle naming | `<brand>-portable.zip` (+ `.sha256` sidecar) |
| Registry dir | `infrastructure/broker-catalog/` |
| Registry schema | `infrastructure/broker-catalog/schema.json` |
| Registry loader | `src/engine/ta/broker/registry.py` |
| Registry API | `GET /api/broker/registry` |
| Pod bundle mount | `/broker-bundle` (read-only in mt-node container) |
| Pod servers.dat target | `<MT_DIR>/config/servers.dat` |
| Bundle-rev annotation | `etradie.io/broker-bundle-sha256` |
| Acquisition URL (human only) | broker official `download.mql5.com/cdn/web/<entity>/mt5/<...>setup.exe` |
| Blocked as fetch path | any URL containing `download.mql5.com` |
| Verification gate | `strings "<prefix>/.../config/servers.dat" \| grep -i <brand>` |
| First two brokers | Deriv (single entity), Exness (primary entity `exness_technologies_ltd`) |
