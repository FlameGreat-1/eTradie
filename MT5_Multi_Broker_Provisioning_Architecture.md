# MT5 Multi-Broker Provisioning — Engineering Architecture Brief

**Exoper Platform — Broker-Agnostic MT5 Account Provisioning**
Prepared for: Engineering Team

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [What Does Not Work (Ruled Out)](#2-what-does-not-work-ruled-out)
3. [The Correct Architecture](#3-the-correct-architecture)
4. [The Broker → Entity → Server Hierarchy](#4-the-broker--entity--server-hierarchy)
5. [Onboarding Wizard: Two-Step Connect Broker Flow](#5-onboarding-wizard-two-step-connect-broker-flow)
6. [Summary: Problem vs Solution](#6-summary-problem-vs-solution)
7. [Implementation Checklist](#7-implementation-checklist)
8. [Why This Is the Industry-Standard Approach](#8-why-this-is-the-industry-standard-approach)

---

## 1. The Problem

### 1.1 What We Are Trying to Do

Exoper provisions a containerized MT5 terminal per tenant (StatefulSet, Service, ServiceAccount, PVC, Vault credentials) so that each user can run automated analysis and trading on their own broker account. The platform is explicitly designed to be broker-agnostic: users connect whichever broker they already trade with.

### 1.2 What Is Confirmed Working

The following infrastructure is provisioned, tested, and functioning correctly:

- Tenant pod creation: StatefulSet, Service, ServiceAccount, PVC, Vault credentials
- The mt-node container image runs; Wine and Xvfb start cleanly
- The MT5 terminal binary launches and compiles inside the Wine prefix
- libzmq.dll and all EA dependencies are present and load correctly
- The LiveUpdate self-restart loop bug is fixed
- `startup.ini` is generated with the correct Login, Password, and Server fields, and the `/config:` flag is honored by the terminal at launch

### 1.3 The Single Remaining Blocker

MT5 never logs in to the broker. Diagnosis confirms:

- No network line indicating a successful server handshake in the terminal log
- Zero Deriv-related entries in the pod's `servers.dat` — confirmed via direct binary inspection (28,544 bytes, entirely populated by other, unrelated brokers)
- `Server=Deriv-Demo` in `startup.ini` has no effect because the terminal has no record of what host/port that name resolves to

### 1.4 Root Cause

`servers.dat` is not a manually editable broker list. It is populated in exactly two ways:

1. Through a live network discovery handshake against MetaQuotes' central broker directory at runtime (requires outbound broadcast-style connectivity that is frequently blocked or unreliable inside containerized/headless environments).
2. Through a broker's own branded MT5 installer, which pre-seeds `servers.dat` with that specific broker's server entries at install time.

Our current image uses the generic MetaQuotes installer, which only ships pre-bundled entries for a small number of major brokers. Deriv — and the majority of brokers our users will bring — are not in that default list. The runtime discovery handshake is the path that is failing.

### 1.5 Why This Is Harder Than a Single-Broker Fix

The platform must support an unknown, growing set of brokers. At 200 users we can reasonably expect 20+ distinct brokers in use. This rules out any solution that assumes a single broker, and it rules out any solution that depends on a runtime mechanism we cannot reliably control inside our container network (the same discovery handshake that is already failing for Deriv).

---

## 2. What Does Not Work (Ruled Out)

Before presenting the correct architecture, the following approaches were investigated and ruled out. This section exists so the team does not re-investigate dead ends.

### 2.1 Manually Editing servers.dat

`servers.dat` is a proprietary binary format, generated and consumed only by the MT5 terminal itself. It is not intended to be hand-edited or templated by third-party tooling. There is no supported, documented way to inject arbitrary broker entries into it directly.

### 2.2 IP:Port Direct Connection as a Universal Bypass

MetaQuotes' own documentation confirms the `Server=` field in a custom `.ini` configuration file accepts the literal format `address:port`, bypassing the named-server lookup. This is real and documented. However:

- It only resolves the named-server lookup step — it does not guarantee the broker's server cluster will accept the connection, since trade servers commonly use TLS/certificate handshakes and load-balanced clusters tied to broker-specific configuration.
- No production system researched (multi-broker VPS providers, MT5 hosting/CRM vendors, liquidity bridge vendors) uses this as a general-purpose, broker-agnostic mechanism.
- **Conclusion:** this is not a verified, scalable solution across an arbitrary set of brokers. It should not be relied upon as the core mechanism.

### 2.3 Relying on Runtime Broker Discovery Inside the Container

This is the mechanism that is already failing for Deriv. It depends on the generic terminal successfully completing a live network discovery handshake against MetaQuotes' broker directory. This handshake is known to be unreliable inside containerized and headless environments, and there is no guarantee it will succeed for any given broker even outside a container. This cannot be the basis of a dependable multi-tenant platform.

---

## 3. The Correct Architecture

### 3.1 Core Principle

> **Broker-agnostic at the platform/orchestration layer. Broker-specific at the installer layer.**

This is the pattern confirmed across every enterprise MT5 hosting, white-label, and multi-broker VPS provider researched. There is no mechanism — documented or undocumented — that makes a single generic MT5 binary work uniformly across arbitrary brokers without broker-specific setup. Every real system in the industry solves this the same way: each broker's own terminal build is installed once, and the platform decides at provisioning time which build to deploy for a given tenant.

Distributing the broker-specific work to the orchestration layer (where we have full control and already have CI/CD automation) rather than depending on runtime network behaviour (where we do not have control) converts an unreliable, opaque problem into a deterministic, testable one.

### 3.2 High-Level Model

```
┌──────────────────────────────────────────────────┐
│   CLOUDFLARE R2 (object storage)                  │
│   Same bucket infrastructure already used for MT5 │
│                                                    │
│  /broker-installers/deriv_setup.exe               │
│  /broker-installers/icmarkets_setup.exe           │
│  /broker-installers/exness_unified_setup.exe      │
│  /broker-installers/ftmo_setup.exe                │
│  ... one entry per broker BRAND we support        │
│  (a single installer typically covers ALL legal   │
│   entities under that brand — see Section 4)      │
└──────────────────┬─────────────────────────────────┘
                   │
      User selects their broker brand, then their
      specific entity, during onboarding (Section 5)
                   │
                   ▼
      Provisioning pipeline resolves brand + entity →
      installer + server list via the Broker Registry
                   │
                   ▼
      Tenant pod build/init step installs that
      brand's branded MT5 build inside the Wine prefix
                   │
                   ▼
      servers.dat is pre-seeded correctly at install
      time — no runtime discovery handshake required
                   │
                   ▼
      startup.ini supplies Login / Password / Server
      — Server is now selected from a populated dropdown,
      not typed manually — MT5 resolves it locally and
      logs in successfully
```

### 3.3 Component 1 — The Broker Registry

A structured table (DB or versioned config file) that is the single source of truth mapping a broker to its provisioning requirements. **Note:** the shape of this record is corrected in Section 4 below — a real broker is not one flat record, but a brand containing multiple legal entities, each with its own server list. See Section 4 for the accurate schema. The simplified single-entity shape below is illustrative only:

```json
{
  "broker_id": "deriv",
  "display_name": "Deriv",
  "installer_path": "r2://exoper-broker-installers/deriv_setup.exe",
  "installer_version": "5.0.0.XXXX",
  "installer_sha256": "<pinned checksum>",
  "demo_server_name": "Deriv-Demo",
  "live_server_names": ["Deriv-Server", "Deriv-Server-02", "Deriv-Server-03"],
  "verified_date": "2026-06-01",
  "status": "active"
}
```

This table is populated once per broker brand we support, not once per user. With 20 broker brands across 200 users, this is 20 top-level entries (each potentially containing several entities), not 200.

### 3.4 Component 2 — Internal Installer Mirror (Cloudflare R2)

All broker installers are downloaded once and mirrored to **Cloudflare R2** — the same object storage already in use for the MT5 terminal binary itself. This is the correct choice over introducing a separate S3 bucket:

- **Zero egress fees on R2**, unlike S3 — every tenant provisioning event fetches a 50–150MB installer; at scale this is a real recurring cost on S3 that R2 eliminates entirely.
- **One bucket infrastructure to manage** — same credentials, same access policies, same monitoring already established for the MT5 binary, rather than standing up and securing a second storage system.
- Never pull broker installers from the public internet at build or provisioning time.
- Pin an exact version and SHA256 checksum per installer, recorded in the Broker Registry.
- Re-verification of a broker's installer is a deliberate, reviewed action — never a silent runtime download.

**Important:** R2 stores the binary. The Broker Registry (a database table) stores the facts *about* that binary — version, checksum, server lists, status. These are not alternatives to each other; the Registry's `installer_path` field is simply a pointer into R2. Both are required, each doing a distinct job.

### 3.5 Component 3 — Provisioning Pipeline Change

The tenant provisioning pipeline gains one new step, inserted before the MT5 terminal is launched for the first time:

1. User finds and selects their broker brand and specific legal entity during onboarding (Section 5 — searchable dropdown sourced from the Broker Registry's active entries, mirroring the native MT5 "Find Broker" experience).
2. Provisioning pipeline looks up the installer path and checksum for that entity's brand.
3. Tenant pod's init step downloads the installer from R2 (never the public CDN) and runs it silently inside the Wine prefix: `xvfb-run wine <brand>_setup.exe /auto`.
4. This pre-seeds `servers.dat` with that brand's correct server entries — covering all of its legal entities — before the terminal is ever started with live credentials.
5. The user selects their **exact server name from a dropdown populated from that entity's stored server list** (not typed manually — see Section 5). `startup.ini` is written with Login / Password / the selected `Server=`, and the terminal now resolves it locally, with no network discovery dependency.

### 3.6 Component 4 — Verification Gate

Before a broker is marked active in the Registry, it must pass a one-time verification check, performed manually or via an automated smoke test:

```bash
strings /path/to/wine/prefix/.../config/servers.dat | grep -i <broker_name>
# → must return non-empty broker server entries
```

This is the same verification discipline already applied to the WineHQ version pin — confirm before trusting, never assume.

### 3.7 Unsupported / Long-Tail Brokers

For brokers outside our actively maintained Registry, the platform should present a clear, honest state rather than a silent failure:

- Onboarding flow flags the broker as "not yet verified" and offers a request/waitlist action.
- Engineering adds new brokers to the Registry on demand, prioritized by user request volume.
- Adding a broker is a bounded, well-defined task: source the broker's branded installer, mirror it internally, verify `servers.dat` population, add one Registry entry. This is operational onboarding work, not a per-broker engineering rebuild.

---

## 4. Summary: Problem vs Solution

| Layer | Current State | Target State |
|---|---|---|
| **Installer** | Generic MetaQuotes `mt5setup.exe` | Broker-specific branded installer, selected per tenant |
| **Server discovery** | Runtime network handshake against MetaQuotes directory (unreliable in container, currently failing) | Pre-seeded `servers.dat` at install time — zero runtime dependency |
| **Broker mapping** | None — assumed single broker | Broker Registry — structured, versioned, one entry per supported broker |
| **Installer source** | Public CDN (mql5.com) — blocked by existing build guard | Internal mirror (S3/Artifactory), pinned + checksummed |
| **Scaling to N brokers** | Undefined / not solved | Linear, bounded: one Registry entry + one installer per broker, reused across all tenants on that broker |

---

## 5. Implementation Checklist

### 5.1 Immediate (Unblock Current Deriv Testing)

1. Source Deriv's official branded MT5 installer from Deriv's own download channel.
2. Mirror it to our internal artifact store; record version + SHA256.
3. Update the tenant init step to install this build instead of the generic `mt5setup.exe`.
4. Re-run provisioning; verify `servers.dat` contains Deriv entries via the `strings | grep` check.
5. Confirm successful login with existing `startup.ini`, unchanged.

### 5.2 Near-Term (Broker Registry Foundation)

1. Stand up the Broker Registry table (DB or versioned config).
2. Define the verification gate / smoke test as a repeatable script, not a manual one-off.
3. Onboard the next 4–5 most-requested brokers using the same process as Deriv.
4. Update the user onboarding flow to select broker from the Registry's active list.

### 5.3 Ongoing (Operational Process)

- New broker requests are triaged and added to the Registry on a defined cadence, not ad hoc.
- Each broker's installer is periodically re-verified (brokers update their installers; pinned versions can go stale).
- Registry entries that fail re-verification are marked inactive until resolved, with onboarding reflecting that status to affected users.

---

## 6. Why This Is the Industry-Standard Approach

This pattern — broker-specific binaries, centrally maintained and selected dynamically per tenant by an orchestration layer — is the consistent model across every MT5 hosting, white-label, and multi-broker VPS provider examined during this investigation (enterprise MT5 management providers, MT5 Manager API vendors, white-label brokerage infrastructure providers, and standard multi-broker VPS setup guides). None of them present a way to make a single generic MT5 binary broker-agnostic at runtime. All of them install each broker's own build, once, and orchestrate around that constraint.

**Adopting this model means Exoper's broker-agnostic promise is delivered correctly: at the orchestration layer, where we have full engineering control, rather than at the MT5 binary layer, where no such control exists.**
