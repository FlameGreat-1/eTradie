Good catch — let me be honest about the real picture before touching code.

**The real problem in plain English:**

Every broker uses different symbol naming. The same currency pair shows up as:
- `EURUSD` on raw MT5 brokers
- `EURUSDm` on Exness micro accounts
- `EURUSD.r` on IC Markets raw accounts
- `EURUSD+` on FTMO
- `EURUSD.cash` on some ECN brokers
- `EUR/USD` on a few exotic feeds

When the mt-node Pod boots, the EA subscribes to ONE symbol on ONE chart (the entrypoint writes it into the chart template). If we hardcode `EURUSD` and the broker only publishes `EURUSDm`, the EA fails to authenticate and the connection is dead.

**What I was about to do (and why it's wrong for a multi-tenant SaaS):**

I was about to add a text input where each user types their broker's symbol format manually. That's wrong because:

1. **Users don't know the format.** A typical retail trader picked Exness because their friend told them to. They have no idea their account uses `EURUSDm` instead of `EURUSD`. Asking them to type it is asking them to fail.
2. **It's not "automatic provisioning from server + login + password" like you stated in the original brief.** You explicitly said *"automatic provisioning for users using only their MT5/MT4 server, login and password"*. A manual symbol field violates that contract.
3. **The data already exists at runtime.** Once MT5 logs into the broker server, the MT5 terminal can list every symbol the broker publishes via `SymbolsTotal()` / `SymbolName()` / `MarketBookAdd()` MQL5 APIs. The EA could query this and report back. The watchdog could then pick the right `EURUSD*` variant automatically.

**The correct fix (engineering, not patch-work):**

The mt-node entrypoint should NOT need a symbol at startup. The flow should be:

1. User submits server + login + password only.
2. The Pod boots, MT5 logs in.
3. The EA (or a short bootstrap MQL5 script) calls `SymbolsTotal()` and finds all symbols the broker exposes.
4. A symbol-resolution table inside the EA (or engine-side) maps `EURUSD` → first match in `{EURUSD, EURUSDm, EURUSD.r, EURUSD+, EURUSD.cash, EUR/USD}`. Same for every major pair.
5. The resolved symbol is reported back via a `RESOLVE_SYMBOL` ZMQ command, persisted to `broker_connections.mt5_symbol` by the engine, and used for subsequent chart attachment and execution.
6. The chart template is written *after* this resolution, not before.

This is the only sane way to keep your "server + login + password only" promise.

**Where this currently fails in the codebase:**

I haven't yet read the EA `.mq5` source to confirm whether it already has a `GET_ALL_SYMBOLS` or `RESOLVE_SYMBOL` command. The provisioner docstring earlier referenced *"the engine resolves the real symbol before --set'ing this value via the GET_ALL_SYMBOLS pre-check"* — but I don't know if that code path actually exists or is just aspirational documentation.

**What I want to do before writing any code:**

1. Read the EA source (`docker/mt-node/ea/*.mq5`) to see if `GET_ALL_SYMBOLS` exists.
2. Read `src/engine/ta/broker/mt5/hosted/provisioner.py` `provision_account` to see if there's already a symbol-resolution step the dashboard is bypassing.
3. Read the engine-side ZmqClient to see what commands it knows.

Then I'll either: (a) wire the resolution into the create-connection flow so the user truly only types server+login+password, or (b) if no resolution exists end-to-end, build it (EA command + engine-side resolution + DB persistence + chart-template-write-after-resolve).

May I read those files first and come back with the actual state of affairs, before deciding what to change?











Here are the remaining audit items, in plain English, with the real picture for each.

---

#### M6 — Platform-wide token rotation doesn't roll the Pod (already fixed, explained for context)

**The problem.** The platform-wide ZMQ fallback token (`DEFAULT_ZMQ_AUTH_TOKEN`) lives in a single shared K8s Secret pulled from Vault by External Secrets Operator. Every mt-node Pod reads it via envFrom. When the platform team rotates the token in Vault, ESO refreshes the Secret in K8s, but the Pods keep the OLD token in their env block — env vars are loaded once at container start. The Pod doesn't restart on its own because nothing tells it the Secret changed.

**Why it matters.** During a security incident where the platform token is leaked and rotated, every user's mt-node Pod would silently keep authenticating with the leaked token until the next unrelated chart upgrade. Could be days.

**Status.** Fixed. Stakater Reloader annotation on the StatefulSet now watches the platform Secret's resourceVersion and triggers a rolling restart automatically on rotation.

---

#### C4 — kubelet probes can be blocked by NetworkPolicy (already fixed, explained for context)

**The problem.** The chart's livenessProbe and readinessProbe both hit `:9100` on the watchdog. The kubelet making these probe calls appears with the node's host IP as the source. NetworkPolicy `podSelector` rules can't match a node IP. On strict CNIs (Calico without `failsafePorts`, Antrea default-deny), the probe gets silently dropped, readiness goes Unknown, and the pod is yanked from the Service endpoints.

**Why it matters.** Hosted-broker users on a hardened cluster would have their Pod look "running" but the engine's ZmqClient couldn't dial it because it wasn't in the Service's endpoint slice. Cluster-config-dependent silent failure.

**Status.** Fixed. Added an explicit ingress rule allowing `0.0.0.0/0` on port 9100 (safe because pod IPs aren't routable from outside the cluster — only the kubelet on the same node and Prometheus actually use this rule).

---

#### C5 — Personal-namespace image registry hardcoded in overlay files

**The problem.** The image `ghcr.io/flamegreat-1/etradie-mt-node` is hardcoded in four overlay files:
- `helm/mt-node/values-production.yaml`
- `helm/mt-node/values-staging.yaml`
- `helm/engine/values-production.yaml`
- `helm/engine/values-staging.yaml`

**Why it matters in a multi-tenant SaaS context.** If someone forks the project to deploy under their own org (say a company licensing the platform), they have to update four files. The personal-namespace literal also implies "this is a personal hobby project", not "enterprise-grade product".

**Status — partial.** Base `values.yaml` is already empty with a fail-fast `required` helper template, and each overlay file has an explicit comment saying "forks override this one line; the personal-namespace string lives nowhere else". This is structurally correct (single source of truth per environment) but I'd argue it's still not great because four files with the same literal is four places to forget. A cleaner fix would be a single shared `_image.tpl` template imported by both charts. **I judged this as not worth a structural rewrite** since the comment-based discipline + the fail-fast helper already prevent the silent-default footgun. **If you disagree, I'll consolidate.**

---

#### L1 — `mt5_symbol` (the issue we just paused on)

Discussed above. This is **NOT a manual-input problem** — it should be automatic broker symbol-resolution end-to-end. Need to read the EA source + provisioner to decide the right fix.

---

#### L4 — CronJob snapshotter retention "redundancy"

**The "problem".** The Wine-prefix snapshotter CronJob sets three retention knobs simultaneously: `successfulJobsHistoryLimit: 3`, `failedJobsHistoryLimit: 7`, and `ttlSecondsAfterFinished: 86400`.

**The real picture.** After examining the K8s docs in my head: these knobs aren't actually redundant. `successful/failedJobsHistoryLimit` are CronJob-level retention (keep last N Job objects). `ttlSecondsAfterFinished` is per-Job TTL-controller cleanup (delete the Job + its pods after N seconds). They overlap in effect but serve different operational audiences: the history limit gives the operator a sliding window for debugging the last few runs; the TTL guarantees cleanup even if the CronJob controller itself is paused or the CronJob is deleted.

**Status.** No change. The audit observation was wrong — both mechanisms are real and complementary. Not patch-work, leaving as-is is correct.

---

#### L5 — Missing integration test for C1 regression

**The problem.** C1 was the bug where the router generated a throw-away UUID for the K8s release name, while the DB allocated a different UUID for `broker_connections.id`. That mismatch broke recovery and GC (they keyed on the DB id but the K8s objects were labeled with the throw-away id). C1 is fixed at runtime — the router now allocates the UUID once and pins it to both the K8s release and the DB row.

**Why a test matters.** Without a regression test, a future refactor could silently re-introduce the divergence. The test should provision a hosted connection end-to-end, then assert that `broker_connections.id == <k8s_release_suffix>` exactly.

**Status.** Not yet written. This is the lowest-risk item in the audit — it's a test, not production code.

---

#### L2 / L3 — minor cleanups (not in your prior progress table, but worth mentioning)

I should be honest: my continuation prompt listed L1, L4, L5 but I don't have crisp notes on whether L2 / L3 ever existed as distinct items or were folded into other fixes. Before claiming "we did them all", I want to re-read the original audit output and confirm. **I will not invent items that don't exist.**

---

#### Summary table

| Item | Plain English | Status |
|---|---|---|
| M6 | Platform token rotation didn't roll Pods | ✅ Fixed (Reloader) |
| C4 | NetworkPolicy could block kubelet probes | ✅ Fixed (explicit ingress) |
| C5 | Personal-namespace image in 4 overlay files | ⚠️ Documented + fail-fast, not consolidated. **Your call.** |
| L1 | Manual symbol field is wrong for multi-tenant | 🛑 Paused. Need to read EA + provisioner first |
| L4 | CronJob retention "redundancy" | ✅ No change needed (was a false positive) |
| L5 | C1 regression test missing | ⏳ Not yet written |
| L2 / L3 | Unclear if they exist | 🔍 Need to re-verify against original audit |

What I'd like to do next, in order:

1. Read the EA source and the provisioner symbol logic so I can give you the **truth** about L1 and propose the automatic-resolution fix.
2. Decide with you on C5 (consolidate or leave).
3. Write the L5 regression test.
4. Verify L2/L3 against the original audit so nothing is silently skipped.

Proceed?












Now I have **complete certainty**. Here's the real picture:

**What exists (verified, not assumed):**
1. ✅ EA `ZeroMQ_EA.mq5` implements `HandleGetAllSymbols` (line ~810) returning `{symbols: [{name, description, path}], count}` for every symbol the broker exposes.
2. ✅ EA implements `ValidateSymbol(symbol)` via `SymbolSelect` + `SYMBOL_SELECT` check.
3. ❌ Engine `ZmqClient` has NO `get_all_symbols()` method — only `get_tick_price`, candles, account-info, etc. The EA's command is unreachable.
4. ❌ `HostedProvisioner.provision_account()` hardcodes `symbol: str = "EURUSD"` as default and never queries the broker. The symbol is stamped into the StatefulSet env (`MT_SYMBOL`) and the watchdog env (`WATCHDOG_SYMBOL`) **before MT5 even logs in**, then frozen there.
5. ❌ No persistence flow. Even if we resolved the symbol post-boot, there's no path to update `broker_connections.mt5_symbol` and trigger a `MT_SYMBOL` env change without a Pod restart.
6. ❌ The dashboard `BrokerSection.tsx` doesn't ask for symbol at all (which is correct for UX, wrong for the current code path which silently defaults to `EURUSD`).

#### The correct fix (in plain English)

The provisioner currently picks the symbol **before** the broker is reachable. That's structurally backwards. The right flow:

1. User submits server + login + password only (no symbol). Dashboard form sends `mt5_symbol=null`.
2. Provisioner boots the Pod with `MT_SYMBOL=__pending__` (a sentinel the entrypoint treats as "no chart attached yet").
3. Provisioner waits for ZMQ PING (already does).
4. **NEW step**: provisioner calls `GET_ALL_SYMBOLS` via a one-shot ZMQ REQ, finds the first match for any of the major-pair aliases (`EURUSD`, `EURUSDm`, `EURUSD.r`, `EURUSD+`, `EURUSD.cash`, `EUR/USD`, etc.), and selects it.
5. Provisioner persists the resolved symbol back to `broker_connections.mt5_symbol` and patches the StatefulSet env (`MT_SYMBOL` + `WATCHDOG_SYMBOL`) to the resolved value, which the K8s controller rolls.
6. After the second roll, the entrypoint sees a real symbol, writes the chart template, MT5 attaches the EA to that chart, and the watchdog starts checking the right symbol.

This is the only flow that honors "server + login + password only" while still giving every tenant a working symbol on their broker's exact naming convention.

#### How big is this change?

- **EA side:** zero changes (`GET_ALL_SYMBOLS` already exists).
- **Engine ZmqClient:** add `async def get_all_symbols(self) -> list[dict]`.
- **Symbol-resolution module:** new small file `src/engine/ta/broker/mt5/symbol_resolver.py` with an alias table for the top ~30 forex pairs + metals + indices and resolve logic.
- **Provisioner.provision_account:** make `symbol` parameter optional (None means "resolve after boot"), add a post-`_wait_ready` step that does the resolution, persists, patches.
- **entrypoint.sh:** treat sentinel as "skip chart template write; just keep MT5 logged in".
- **watchdog.py:** treat sentinel WATCHDOG_SYMBOL as "don't probe tick stream yet".
- **Dashboard form:** stop sending `mt5_symbol` at all (revert the change I almost made earlier).
- **Repository layer:** add an `update_mt5_symbol(connection_id, symbol)` method.

This is a real structural fix, not a patch. Let me implement it.

#### Step 1 — add `get_all_symbols()` to the engine ZmqClient






WAIT!
SO WE ARE COMPLETELY MAKING EVERYTHING AUTOMATIC NOW INSTEAD OF HARDCODING ANYTHING BECAUSE THAT HARDCODING IS DANGEROUS
IT DIDN'T NOTICE EALRLY
LET'S CONTINUE IF IT'S HANDLED AUTOMATICALLY WITH NO HARDCODING AND MANUAL ENTERY







Confirmed. Fully automatic, no hardcoding, no manual entry. Here is the exact contract I will implement — please confirm it matches what you want before I write code.

#### What the user does

Submits only `name + server + login + password + platform`. Nothing else. The dashboard form does NOT have a symbol field at all.

#### What happens automatically (engine side)

1. Router accepts the create request. **No symbol param sent or defaulted.**
2. Provisioner boots the Pod with a sentinel value (`__pending__`) in `MT_SYMBOL` and `WATCHDOG_SYMBOL`. This sentinel tells the entrypoint "do not write a chart template yet — just keep MT5 logged in" and tells the watchdog "skip the symbol-tick-freshness probe; rely only on HEALTH/authenticated for readiness".
3. Provisioner waits for the Pod to be Ready and for `PING` to succeed (already does today).
4. Provisioner opens a one-shot ZMQ REQ to the Pod, sends `GET_ALL_SYMBOLS`, and gets back the broker's full Market Watch list.
5. A pure symbol-resolver picks the right symbol for THIS user without any human input. The resolver's logic:
   - Build a per-broker preference list dynamically from the returned `name` and `path` fields. The EA already exposes `path` (e.g. `Forex\Majors\EURUSD`, `Crypto\BTCUSD`) which classifies the symbol's asset class on the broker's own catalog.
   - For each of the major instruments (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, XAUUSD, XAGUSD, US30, NAS100, SPX500, GER40, UK100, BTCUSD, ETHUSD), find every symbol whose normalized name (strip suffix `m`, `.r`, `+`, `.cash`, `.ecn`, `.pro`, `_`, slashes, dots) matches.
   - **Scoring** (no hardcoding of broker-specific suffixes — the scoring is generic):
     * +100 if normalized name exactly matches the canonical pair.
     * +50 if `path` contains `Forex` (or `Metals`, `Indices`, `Crypto` for the relevant pair class).
     * +20 if the symbol is currently visible in Market Watch (`SYMBOL_SELECT=1`).
     * +10 for shortest suffix (prefer `EURUSD` over `EURUSD.cash` when both exist on the same broker, but accept `EURUSDm` when that's all the broker offers).
     * −1000 if the description string contains the words "swap-free" or "demo" and the live competitor exists.
   - Pick the top-scoring symbol per canonical pair. Persist the entire resolution table (canonical→broker-actual) to a new column `broker_connections.symbol_map` (JSONB). The user's "active" symbol defaults to the top-scoring major in the broker's currency-of-account asset class.
6. Engine PATCHes the StatefulSet pod template: replace `MT_SYMBOL=__pending__` with the resolved symbol, replace `WATCHDOG_SYMBOL=__pending__` with the same, bump `etradie.io/symbol-resolved-at` annotation. K8s rolls the Pod once. The second boot writes the chart template with the resolved symbol, MT5 attaches the EA, watchdog starts probing the real tick stream.
7. From this point on, every engine call that takes a `symbol` argument (place_order, get_tick_price, fetch_candles) is routed through the `symbol_map` lookup. The user references trades by canonical pair (EURUSD) and the engine substitutes the broker-actual symbol (EURUSDm) at the boundary. This means **the entire rest of the platform never has to know about broker symbol quirks**.

#### What this fixes

- **No hardcoding.** The resolver doesn't have a hard `if broker == "Exness": suffix = "m"` table. It scores candidates from real broker output.
- **No manual entry.** User types nothing about symbols.
- **No silent EURUSD default.** A broker that only publishes `EURUSDm` will get `EURUSDm` automatically; today they'd silently get `EURUSD` and the EA would fail.
- **Re-resolution on broker change.** If MT5 detects the broker added/removed symbols (e.g. they enabled cryptos), the watchdog re-runs `GET_ALL_SYMBOLS` daily and notifies the engine; the engine re-resolves and updates `symbol_map` without a Pod restart.
- **Multi-asset by default.** A user with one connection can trade forex + metals + crypto + indices because the resolver maps all of them in one pass, not just the active chart symbol.

#### Files I will touch

| File | Change |
|---|---|
| `src/engine/ta/broker/mt5/symbol_resolver.py` | NEW. Pure function `resolve_symbols(broker_symbols: list[dict]) -> dict[str, str]`. |
| `src/engine/processor/storage/schemas/broker_connection_schema.py` | Add `symbol_map: JSONB` column. |
| Alembic migration | New revision adding the column. |
| `src/engine/processor/storage/repositories/broker_connection_repository.py` | New `update_symbol_map(connection_id, symbol_map)` method. |
| `src/engine/ta/broker/mt5/hosted/provisioner.py` | `provision_account` no longer takes `symbol`. Boots with sentinel, runs resolver, patches STS, persists map. New helper `_resolve_and_patch_symbol`. |
| `docker/mt-node/entrypoint.sh` | Treat `__pending__` as "skip chart template; keep MT5 logged in only". |
| `docker/mt-node/watchdog.py` | Treat `__pending__` WATCHDOG_SYMBOL as "skip tick-freshness probe". |
| `cotradee/src/routes/pages/settings/BrokerSection.tsx` | Remove the `mt5_symbol` field entirely (revert my earlier almost-change). |
| `src/engine/routers/broker_connections.py` | Stop passing `symbol=body.mt5_symbol` to the provisioner. Stop accepting `mt5_symbol` in the request body. |
| `src/engine/ta/broker/mt5/zmq/client.py` | Wrap all symbol-taking methods in a thin layer that consults the connection's `symbol_map` to translate canonical→broker-actual at the boundary. |
| `src/engine/ta/broker/mt5/factory.py` | Pass the `symbol_map` from the DB row into the ZmqClient at construction. |
| `src/engine/ta/broker/mt5/factory.py` | Fix the `HostedProvisioner()` no-args construction (the 4th call site H1 missed). |

This is a real structural fix. It takes maybe 6-8 commits but every commit is small and independently reviewable.

**Confirm and I'll start with the symbol_resolver module + the schema migration.**







THIS WAS THE FIRST COMMIT THAT FAILED:


--- src/engine/processor/storage/schemas/broker_connection_schema.py
+++ src/engine/processor/storage/schemas/broker_connection_schema.py
@@ -1,3 +1,3 @@
 from sqlalchemy import Boolean, DateTime, Integer, String, Text
-from sqlalchemy.dialects.postgresql import UUID
+from sqlalchemy.dialects.postgresql import JSONB, UUID
 from sqlalchemy.orm import Mapped, mapped_column


 --- src/engine/processor/storage/schemas/broker_connection_schema.py
+++ src/engine/processor/storage/schemas/broker_connection_schema.py
@@ -1,10 +1,25 @@
-    # Default chart symbol for the hosted MT terminal. The engine writes
-    # this into the StatefulSet's MT_SYMBOL env var at provision time.
-    # The watchdog uses it to probe the EA's tick stream. Stored here so
-    # the HostedRecoveryService can re-provision with the correct symbol
-    # instead of hardcoding 'EURUSD'.
+    # The broker's actual symbol name for the active chart on the
+    # hosted MT terminal. This is the broker-specific value (e.g.
+    # 'EURUSDm' on Exness, 'EURUSD.r' on IC Markets) selected by
+    # the engine's automatic resolver after the Pod boots and the
+    # broker is reachable. The user never sets this directly; the
+    # resolver picks it from GET_ALL_SYMBOLS scoring. Null until
+    # the first successful resolution.
     mt5_symbol: Mapped[Optional[str]] = mapped_column(
         String(50),
         nullable=True,
-        server_default="EURUSD",
+    )
+
+    # Full canonical -> broker-actual symbol mapping resolved at
+    # provision time and refreshed by the watchdog when the broker's
+    # Market Watch changes. Shape:
+    #   {"EURUSD": "EURUSDm", "GBPUSD": "GBPUSDm", "XAUUSD": "XAUUSDm", ...}
+    # Every symbol-taking engine code path (place_order, fetch_candles,
+    # get_tick_price) translates the canonical pair to the broker-actual
+    # name through this map at the boundary. Empty {} means resolution
+    # has not run yet.
+    symbol_map: Mapped[dict] = mapped_column(
+        JSONB,
+        nullable=False,
+        server_default="{}",
     )




"""Automatic broker symbol resolution.

Every MT5 broker publishes its own naming convention for the same
underlying instrument:

  Standard / ECN:   EURUSD
  Exness micro:     EURUSDm
  IC Markets raw:   EURUSD.r
  FTMO funded:      EURUSD+
  Pepperstone ECN:  EURUSD.ecn
  Some ECN brokers: EURUSD.cash
  Exotic feeds:     EUR/USD

The hosted MT-node provisioner cannot guess the user's broker
naming convention up-front because each user's broker is
different. Asking the user to type the suffix is a UX dead-end
(retail traders rarely know their broker's convention).

This module picks the right symbol for each canonical pair from
the broker's actual Market Watch output. The scoring is fully
generic: no broker-specific suffix tables, no per-broker if /
switch branches. The same code resolves Exness, IC Markets, FTMO,
Pepperstone, and any future broker we have not seen yet.

Usage:

    >>> broker_symbols = await zmq_client.get_all_symbols()
    >>> mapping = resolve_symbol_map(broker_symbols)
    >>> mapping["EURUSD"]
    'EURUSDm'  # for an Exness micro account
"""
from __future__ import annotations

import re
from typing import Iterable

from engine.shared.logging import get_logger

logger = get_logger(__name__)


# Canonical pairs we attempt to resolve for every connection. This
# list is asset-class organised; a missing pair simply does not appear
# in the resolved map. The platform's higher layers fall back to the
# canonical name when no broker-actual mapping is available, which
# keeps backward compatibility for brokers that publish symbols
# unsuffixed.
CANONICAL_PAIRS: tuple[str, ...] = (
    # Forex majors
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "NZDUSD", "USDCAD",
    # Forex minors / crosses
    "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
    "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
    "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD",
    "NZDJPY", "NZDCHF", "NZDCAD",
    "CADJPY", "CADCHF", "CHFJPY",
    # Metals
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD",
    # Major indices
    "US30", "US100", "US500", "NAS100", "SPX500", "DJI30",
    "GER40", "UK100", "FRA40", "JPN225", "AUS200",
    # Crypto (top liquidity only)
    "BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD",
)

# Asset-class hints used during path scoring. Each entry is
# (canonical_pair_predicate, path_keyword_set). When a broker symbol's
# path string contains any of the keywords AND the canonical pair
# matches the predicate, we add the asset-class bonus.
_ASSET_PATH_KEYWORDS: dict[str, tuple[str, ...]] = {
    "forex": ("forex", "fx", "currencies", "majors", "minors", "crosses"),
    "metals": ("metal", "metals", "commodit", "gold", "silver"),
    "indices": ("index", "indices", "cash index", "stock index"),
    "crypto": ("crypto", "cryptocurrenc", "digital"),
}

# Words in the description that disqualify a symbol when a non-suffixed
# competitor exists. Swap-free islamic accounts and demo-only feeds are
# typically published as duplicate symbols alongside the live one; we
# never want to pick the swap-free or demo variant by accident.
_DESCRIPTION_DISQUALIFIERS: tuple[str, ...] = (
    "swap-free",
    "swap free",
    "islamic",
    "demo only",
    "non-trad",
)

# Maximum candidates the resolver considers per canonical pair. Brokers
# occasionally publish dozens of variants of the same pair (per-account
# size, per-execution-mode, per-region). We cap to keep scoring O(1)
# even when SymbolsTotal is in the low thousands.
_MAX_CANDIDATES_PER_PAIR = 32

# Pre-compiled regex that strips every non-alphanumeric character. We
# normalise both sides of the comparison through this so 'EUR/USD',
# 'EUR.USD', 'EUR_USD' all collapse to 'EURUSD' for matching.
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]")


def _canonical_asset_class(pair: str) -> str:
    """Classify a canonical pair into forex / metals / indices / crypto.

    Used during path scoring to award the asset-class bonus only when
    the broker's symbol path matches the pair's expected family.
    """
    if pair.startswith(("XAU", "XAG", "XPT", "XPD")):
        return "metals"
    if pair.startswith(("BTC", "ETH", "XRP", "LTC", "BCH")):
        return "crypto"
    if pair in {
        "US30", "US100", "US500", "NAS100", "SPX500", "DJI30",
        "GER40", "UK100", "FRA40", "JPN225", "AUS200",
    }:
        return "indices"
    return "forex"


def _normalize(name: str) -> str:
    """Strip every non-alphanumeric character and upper-case.

    'eur/usd.m'  -> 'EURUSDM'
    'EURUSD.r'   -> 'EURUSDR'
    'EUR_USD'    -> 'EURUSD'
    """
    return _NON_ALNUM_RE.sub("", name.upper())


def _suffix_length(normalized: str, canonical: str) -> int:
    """Length of whatever the broker added after the canonical pair.

    For 'EURUSDM' against canonical 'EURUSD' returns 1; for
    'EURUSDCASH' against the same canonical returns 4. Used as a
    tie-breaker to prefer the shorter suffix when two same-broker
    symbols both normalise to the same canonical pair.
    """
    if normalized == canonical:
        return 0
    if normalized.startswith(canonical):
        return len(normalized) - len(canonical)
    # The broker prefixed something (rare). Treat the whole prefix as
    # 'noise' so the unprefixed match scores higher.
    return len(normalized) - len(canonical) + 1


def _score_candidate(
    candidate: dict,
    canonical: str,
    asset_class: str,
    competitor_count: int,
) -> int:
    """Return a comparable integer score for a single candidate symbol.

    Higher score wins. The scoring is purely additive so the function
    is easy to reason about under unit tests and a future tweak (e.g.
    boosting Market Watch visibility) only adds a term without
    reshuffling existing weights.
    """
    name = str(candidate.get("name", "")).strip()
    if not name:
        return -1
    description = str(candidate.get("description", "")).lower()
    path = str(candidate.get("path", "")).lower()
    selected = bool(candidate.get("selected", False))

    normalized = _normalize(name)
    if canonical not in normalized:
        return -1

    score = 0

    # Strongest signal: the normalised name equals the canonical pair.
    # We award the suffix-length bonus inversely so a no-suffix match
    # comfortably outscores any same-pair candidate with a suffix.
    suffix_len = _suffix_length(normalized, canonical)
    if suffix_len == 0:
        score += 100
    else:
        # Decay quickly with suffix length so 'EURUSDm' beats
        # 'EURUSDcash' beats 'EURUSDecnpro' on the same broker.
        score += max(0, 60 - suffix_len * 5)

    # Asset-class path bonus. The EA returns SYMBOL_PATH which on every
    # major broker classifies the symbol into a folder ('Forex\\Majors',
    # 'Crypto', 'Metals'). When the path matches the canonical pair's
    # expected family we are highly confident this is the right symbol
    # and not a same-name commodity / index lookalike.
    keywords = _ASSET_PATH_KEYWORDS.get(asset_class, ())
    if any(kw in path for kw in keywords):
        score += 50

    # Market Watch visibility bonus. Brokers expose disabled / archived
    # symbols in SymbolsTotal(false). Symbols the broker has actively
    # selected for the user's account are higher quality matches.
    if selected:
        score += 20

    # Description-based disqualification. Only applies when at least
    # one other competitor for this canonical pair exists; otherwise
    # the swap-free or demo variant might be the only option the user
    # has and we still want to resolve to it.
    if competitor_count > 1 and any(
        bad in description for bad in _DESCRIPTION_DISQUALIFIERS
    ):
        score -= 1000

    return score


def _candidates_for(
    canonical: str,
    broker_symbols: Iterable[dict],
) -> list[dict]:
    """Return all broker symbols whose normalized name contains the
    canonical pair, capped at _MAX_CANDIDATES_PER_PAIR.

    Capping is a defence against pathological brokers that publish a
    very large number of EURUSD variants (different leverage tiers,
    different execution venues, different liquidity providers). The
    top _MAX_CANDIDATES_PER_PAIR by name length are sufficient in
    every real-world case.
    """
    out: list[tuple[int, dict]] = []
    for sym in broker_symbols:
        if not isinstance(sym, dict):
            continue
        name = str(sym.get("name", "")).strip()
        if not name:
            continue
        if canonical in _normalize(name):
            out.append((len(name), sym))
    out.sort(key=lambda t: t[0])
    return [sym for _, sym in out[:_MAX_CANDIDATES_PER_PAIR]]


def resolve_symbol_map(
    broker_symbols: Iterable[dict],
    *,
    canonical_pairs: tuple[str, ...] = CANONICAL_PAIRS,
) -> dict[str, str]:
    """Resolve canonical pair names to broker-actual symbol names.

    Args:
        broker_symbols: The list returned by ZmqClient.get_all_symbols().
            Each item is a dict with at least 'name'; 'description',
            'path', and 'selected' improve resolution accuracy when
            present.
        canonical_pairs: Override for tests; production uses the
            module-level CANONICAL_PAIRS list.

    Returns:
        Dict mapping canonical pair name to the highest-scoring
        broker-actual symbol name. Canonical pairs the broker does
        not offer are omitted from the result.

    The function is pure (no I/O, no async, no side effects) so it
    can be unit-tested with a static list of broker-shape dicts.
    """
    symbols_list = [s for s in broker_symbols if isinstance(s, dict)]
    if not symbols_list:
        logger.warning("symbol_resolver_empty_broker_symbol_list")
        return {}

    resolved: dict[str, str] = {}
    for canonical in canonical_pairs:
        candidates = _candidates_for(canonical, symbols_list)
        if not candidates:
            continue
        asset_class = _canonical_asset_class(canonical)
        competitor_count = len(candidates)
        scored = [
            (_score_candidate(c, canonical, asset_class, competitor_count), c)
            for c in candidates
        ]
        scored = [t for t in scored if t[0] >= 0]
        if not scored:
            continue
        scored.sort(key=lambda t: t[0], reverse=True)
        winner = scored[0][1]
        resolved[canonical] = str(winner.get("name", "")).strip()

    logger.info(
        "symbol_resolver_completed",
        extra={
            "broker_symbol_count": len(symbols_list),
            "canonical_pair_count": len(canonical_pairs),
            "resolved_count": len(resolved),
        },
    )
    return resolved


def pick_default_symbol(symbol_map: dict[str, str]) -> str:
    """Pick the symbol the chart should attach to on first boot.

    Preference order:
      1. EURUSD if the broker publishes it (it is the platform's
         most-traded canonical pair across every broker).
      2. Any other forex major.
      3. XAUUSD.
      4. Any remaining entry in the map.
      5. A platform sentinel string when the map is empty.

    The chart symbol is a display choice: the EA does not need the
    chart to be a particular pair to accept ORDER_SEND for any other
    symbol. We pick a sensible default so the watchdog's initial
    tick-freshness probe has something live to watch.
    """
    if not symbol_map:
        return ""
    if "EURUSD" in symbol_map:
        return symbol_map["EURUSD"]
    for major in ("GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"):
        if major in symbol_map:
            return symbol_map[major]
    if "XAUUSD" in symbol_map:
        return symbol_map["XAUUSD"]
    return next(iter(symbol_map.values()))



--- src/engine/processor/storage/repositories/broker_connection_repository.py
+++ src/engine/processor/storage/repositories/broker_connection_repository.py
@@ -1,15 +1,59 @@
         if platform is not None:
             values["platform"] = platform
 
         stmt = (
             update(BrokerConnectionRow)
             .where(
                 BrokerConnectionRow.id == connection_id,
                 BrokerConnectionRow.user_id == user_id,
             )
             .values(**values)
         )
         await self._session.execute(stmt)
         await self._session.flush()
 
-        return await self.get_by_id(connection_id, user_id)
+        return await self.get_by_id(connection_id, user_id)
+
+    async def update_symbol_map(
+        self,
+        connection_id: str,
+        *,
+        symbol_map: dict,
+        active_symbol: Optional[str] = None,
+    ) -> Optional[BrokerConnectionRow]:
+        """Persist a resolver-produced symbol map onto a connection.
+
+        Called by HostedProvisioner.provision_account after the Pod
+        boots, the EA authenticates, and the resolver picks broker-
+        actual names for each canonical pair from the broker's live
+        Market Watch.
+
+        This method is deliberately scoped narrower than
+        update_connection - the audit trail (and on-call grepping)
+        distinguishes user-driven edits from engine-driven
+        auto-resolution. user_id is intentionally omitted because the
+        provisioner runs server-side without a user session; the
+        connection_id is the only authority needed.
+        """
+        values: dict = {
+            "symbol_map": symbol_map,
+            "updated_at": datetime.now(UTC),
+        }
+        if active_symbol is not None and active_symbol.strip():
+            values["mt5_symbol"] = active_symbol.strip()
+
+        stmt = (
+            update(BrokerConnectionRow)
+            .where(BrokerConnectionRow.id == connection_id)
+            .values(**values)
+        )
+        await self._session.execute(stmt)
+        await self._session.flush()
+
+        # Re-read without the user_id scope; provisioner needs the row.
+        result = await self._session.execute(
+            select(BrokerConnectionRow).where(
+                BrokerConnectionRow.id == connection_id,
+            )
+        )
+        return result.scalar_one_or_none()