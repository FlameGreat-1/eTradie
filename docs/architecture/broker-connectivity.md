# Broker connectivity design (REQ/REP contract)

Authoritative design doc for the engine's broker-side connectivity
layer. This document exists because an audit reviewer reading
`src/engine/ta/broker/mt5/zmq/client.py` and the CHECKLIST Section 2
line 'No tick data loss during reconnect' could reasonably ask:
"REQ/REP is request-driven; how does the engine guarantee no tick
loss?".

The answer: REQ/REP being request-driven IS the guarantee, not a
defect. This document spells out the invariants so a future engineer
reviewing the code does not waste time re-deriving them.

## Tick-read invariants

Given a call to `ZmqClient.get_tick_price(symbol)`:

1. **Each tick read is a stateless REQ/REP round-trip.** No tick
   stream exists in the engine; the EA produces ticks continuously
   inside MT5 but the engine fetches them on demand via the
   `TICK_PRICE` command.

2. **TickFreshnessGuard rejects stale replies.** The reply's
   `tick.time` is compared against the engine's clock
   (compensated by `ClockSkewMonitor`); if `age > tickMaxAgeSecs`
   (default 10s) the call raises `ProviderStalePriceError`. The
   caller treats this as a degraded broker, not as a returned
   price.

3. **Reconnect is per-request.** On a ZMQ-socket error the client
   destroys the trading socket (`_socket.close(linger=0)` and
   `_initialized = False`) so the NEXT request opens a fresh
   socket. The `ReconnectPolicy` (full-jitter exponential
   backoff, base 1s cap 30s, max 10 attempts) drives the retry
   schedule.

4. **No queued tick can be lost.** There is no engine-side queue
   to lose. A failed `get_tick_price` either:
   - raises `ProviderTimeoutError` (broker is unreachable -> caller
     decides whether to retry the SAME request);
   - raises `ProviderStalePriceError` (broker returned a tick but
     it is too old -> caller treats as no-tick); or
   - returns a fresh `TickPrice` (success - within `tickMaxAgeSecs`).

   There is no fourth outcome.

5. **The retried request is a NEW request.** When the caller
   retries after a `ProviderTimeoutError`, that retry is a brand-new
   `TICK_PRICE` command against the broker. The broker computes the
   reply from the broker-side state AT THE MOMENT OF THE RETRY,
   which is the freshest tick available. Nothing about the
   pre-disconnect tick stream affects the post-disconnect reply.

## What CHECKLIST Section 2 'No tick data loss during reconnect' means

The CHECKLIST item exists because some broker bridges DO have a
streaming tick pipeline (e.g. a continuous PUB/SUB feed). On those
bridges, a reconnect window could drop ticks that were on the wire
at the time. eTradie's bridge is REQ/REP - the failure mode the
CHECKLIST guards against does not apply by construction.

The CHECKLIST Section 2 line is therefore satisfied as 'N/A by
design'. The operator-facing evidence:

- `etradie_broker_reconnect_attempts_total{provider, account_id}` -
  cumulative reconnect attempts. Used by the existing
  PrometheusRule to alert on flapping connections.
- `etradie_broker_tick_stale_total{provider, account_id, symbol}` -
  cumulative TickFreshnessGuard rejections. A non-zero rate is the
  signal that the broker is returning stale data, NOT that the
  engine is dropping ticks.
- `etradie_broker_tick_fetch_recovery_total{provider, account_id}` -
  cumulative successful `get_tick_price` calls that fired within
  `_TICK_RECOVERY_WINDOW_SECS` of a reconnect. PromQL-verifiable
  recovery evidence.

## Tick-recovery SLO

Add this to the engine PrometheusRule (`helm/engine/templates/
prometheusrule.yaml`) when ready to enforce the SLO at the alert
layer:

```yaml
- alert: EngineTickRecoverySlowAfterReconnect
  expr: |
    (
      sum by (provider, account_id) (
        increase(etradie_broker_reconnect_attempts_total[5m])
      ) > 0
    )
    and
    (
      sum by (provider, account_id) (
        increase(etradie_broker_tick_fetch_recovery_total[5m])
      ) == 0
    )
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "reconnect occurred but no successful tick fetch within 5m"
    runbook_url: "https://docs.etradie.com/runbooks/engine-tick-recovery-slow"
```

The alert fires when a reconnect happened (numerator > 0) AND no
tick recovery succeeded within the same 5m window. That is the
empirical signal that the design invariant above is being violated
in practice.

## ReqRep vs PubSub: why we chose ReqRep

A prior design draft proposed a continuous PUB/SUB tick stream
between the EA and the engine. We rejected it because:

- PUB/SUB has no acknowledgement, so a slow consumer drops messages
  silently. The engine's tick consumer is bounded by the
  TickFreshnessGuard's serialised path; under load the engine would
  silently drop the freshest ticks while the worker is busy.

- PUB/SUB cannot multiplex symbols within a single socket without
  introducing a subscription layer that itself can drop
  subscriptions on reconnect (libzmq's xpub/xsub).

- The engine's analysis cycle is on a 60s cadence; per-tick latency
  beyond ~250ms does not affect decision quality. REQ/REP's
  request-driven model gives us exactly-once tick semantics on the
  engine-side at a latency that comfortably meets the SLO.

The trade-off is bandwidth: REQ/REP transmits one TICK_PRICE
round-trip per analysis cycle per symbol, whereas PUB/SUB would have
streamed every tick. At the platform's planned 1000-user / N-symbol
target, REQ/REP's bandwidth is bounded by `users * symbols *
(cycles/minute) * payload_bytes`, which at the default tuning
(60s cycle, ~512B payload, 5 symbols/user) is ~6MB/min/1000 users.
Well inside any cloud-egress envelope.
