# L1 — Automatic Broker Symbol Resolution

Fully automatic canonical -> broker-actual symbol resolution end to
end. Replaces the 'EURUSD' silent default + manual symbol input on
the dashboard with a generic scoring resolver that runs once after
the Pod boots, persists the map to broker_connections.symbol_map,
and is reused by every symbol-taking engine code path.

No broker-specific if-branches, no per-broker suffix tables. Same
code resolves Exness, IC Markets, FTMO, Pepperstone, and any future
broker we have not seen yet.

## Phase status

| Phase | Scope | Status |
|------:|---|---|
|  1 | DB foundation: schema column, migration 0030, repo `update_symbol_map`, repo `update_connection` accepts `mt5_symbol`. | ✅ this commit |
|  2 | Pure resolver module `engine.ta.broker.mt5.symbol_resolver` with `resolve_symbol_map()` and `pick_default_symbol()`. | ⏳ |
|  3 | Provisioner rewrite: boot with `__pending__` sentinel, post-`_wait_ready` resolve via ZMQ `GET_ALL_SYMBOLS`, persist, then patch the StatefulSet env so K8s rolls the Pod once. | ⏳ |
|  4 | `entrypoint.sh` + `watchdog.py` sentinel handling: skip chart template + tick probe while `MT_SYMBOL=__pending__`. | ⏳ |
|  5 | Router + `CreateBrokerConnectionRequest`: stop accepting `mt5_symbol` from clients. Surface resolved `symbol_map` + `mt5_symbol` in the response. | ⏳ |
|  6 | `ZmqClient` canonical->broker-actual translation layer + `factory.py` reads `row.symbol_map` and injects it. Fix bare `HostedProvisioner()` no-args call (H1). | ⏳ |
|  7 | `recovery.py`: stop defaulting `symbol='EURUSD'`; forward `row.mt5_symbol` (or None) to the rewritten provisioner. | ⏳ |
|  8 | Dashboard `SymbolsSection.tsx` rebuild: replace free-form text input with picker reading the user's broker symbol catalog. | ⏳ |
|  9 | Gateway `setSymbols`: validate against the user's `symbol_map`; reject unknown strings with 400. | ⏳ |
| 10 | L5 regression test asserting `broker_connections.id == k8s_release_name_suffix`. | ⏳ |
| 11 | Cleanup: remove orphan `ENGINE_CONNECTIVITY_SYMBOL_RESOLVER_CACHE_TTL_SECS` env var from ConfigMap + values.yaml. Replace aspirational comment in `helm/mt-node/values.yaml`. | ⏳ |
| 12 | Final summary commit + PROGRESS update. | ⏳ |

## Design (verified against the codebase, not against docs)

**EA contract.** `docker/mt-node/ea/ZeroMQ_EA.ex5` (source
`src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5`) exposes
`GET_ALL_SYMBOLS` (verified at line ~805 of the mq5 source). The
return shape is `{symbols:[{name,description,path}], count}`. There
is NO `selected` field in the EA response; the resolver scoring
function has been adjusted to match the actual EA contract, not a
docstring guess.

**broker_symbols table.** Migration `0018_add_broker_symbols_table.py`
already exists. It is populated lazily by `BrokerSyncService.
sync_all_symbols()` (one row per broker symbol with full metadata
including `path`, `digits`, `point`) and consumed by the dashboard
chart's `/api/broker/symbols` endpoint. This table is the **per-
symbol metadata catalog**. The resolver's output is a different
shape — the **canonical -> broker-actual mapping** — so it gets its
own column on `broker_connections` (single source of truth per
connection, no cross-table joins needed at hot path).

**Vault secrets.** `infrastructure/cluster/vault-paths/
mt_node_tenant_secrets.tf` stores only `mt5_login`, `mt5_password`,
`mt5_zmq_auth_token`. No symbol stored in Vault — correct, because
the symbol is non-secret per-tenant Postgres state.

**Helm chart.** `helm/mt-node/templates/statefulset.yaml` bakes
`MT_SYMBOL` from `.Values.mtConnection.symbol`. The engine-runtime
path constructs the StatefulSet directly via `kubernetes_asyncio`
and patches `MT_SYMBOL` post-resolution. The chart-rendered platform
path (used only for `mtConnection.enabled=false` cluster-level
render) renders only the cluster-scoped resources and never the
per-tenant StatefulSet, so no symbol value flows through it.

## Resume contract

If this chat ends mid-implementation, the next session can resume by
reading this file's phase status table. Every phase's commit message
starts with `L1 Phase N/12: …` so the audit log is searchable.
