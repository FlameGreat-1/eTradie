

Below is a **production-grade readiness checklist** for self-hosted MT4/MT5 (Wine-based or terminal-based) trading infrastructure.

This is the engineering spec for the team to work from.

---

# 🧠 1. CORE MT TERMINAL STABILITY LAYER (CRITICAL)

These are non-negotiable before self-hosting.

### Terminal lifecycle stability

* [ ] MT4/MT5 terminals start reliably (100% automated boot)
* [ ] Terminals auto-restart on crash
* [ ] No manual intervention required to recover terminals
* [ ] Persistent session recovery after VPS reboot
* [ ] Graceful shutdown handling (no corrupted state)

---

### Memory stability

* [ ] No memory leaks in Wine + MT terminal over 24–72h uptime
* [ ] Memory usage per terminal is bounded (hard limits enforced)
* [ ] Automatic restart if memory exceeds threshold (watchdog)
* [ ] Garbage process cleanup (zombie MT/Wine processes)

---

### CPU stability

* [ ] Indicator recalculation spikes do not freeze system
* [ ] CPU throttling per terminal is enforced
* [ ] Load balancing across cores (no core starvation)

---

# 🔌 2. BROKER CONNECTIVITY & RESILIENCE

This is where most self-host systems fail.

### Connection stability

* [ ] Automatic reconnection on broker disconnect
* [ ] Detection of “silent disconnect” (no data but socket alive)
* [ ] Heartbeat system per MT terminal
* [ ] Re-login automation on session expiry

---

### Market data integrity

* [ ] No tick data loss during reconnect
* [ ] No duplicated ticks after reconnection
* [ ] Price feed validation layer (anti-stale pricing detection)

---

### Multi-broker handling

* [ ] Broker-specific configuration isolation
* [ ] No cross-broker contamination (logs, cache, symbols)
* [ ] Symbol mapping consistency layer

---

# ⚙️ 3. EXECUTION ENGINE RELIABILITY

This is your “money layer”.

### Order execution correctness

* [ ] No duplicate orders (idempotency layer)
* [ ] Order confirmation verification system
* [ ] Retry logic with backoff (not blind retries)
* [ ] Partial fill handling correctly implemented

---

### Latency handling

* [ ] Execution latency measured per order
* [ ] Orders rejected if latency exceeds threshold
* [ ] Queue system for bursts (no execution storm collapse)

---

### Failure handling

* [ ] Failed orders logged with full context
* [ ] Automatic reconciliation system (sync broker vs system state)
* [ ] Trade state recovery after crash

---

# 🧩 4. EA (EXPERT ADVISOR) STABILITY

This is often overlooked — and very dangerous.

### EA lifecycle

* [ ] EA auto-restarts after terminal restart
* [ ] EA state persistence (no loss of strategy state)
* [ ] No duplicate EA instances per chart

---

### EA desync prevention

* [ ] Detect EA vs backend signal mismatch
* [ ] Periodic state reconciliation between EA and backend
* [ ] Kill-switch if EA diverges from expected logic

---

### Strategy execution integrity

* [ ] Deterministic signal handling (same input = same action)
* [ ] No race conditions between multiple signals
* [ ] Time synchronization (critical for trading logic)

---

# 🧠 5. SYSTEM SCALING & LOAD CONTROL

This is where your earlier assumptions break.

### Load isolation

* [ ] One MT terminal cannot affect another
* [ ] Resource isolation per user (cgroups or equivalent)
* [ ] No shared memory corruption risk

---

### Scaling behavior

* [ ] Predictable resource usage per new user
* [ ] No exponential CPU spikes under load
* [ ] No cascading failure when 1 terminal crashes

---

### Burst handling

* [ ] Market open / news spike handling
* [ ] Order burst queue system
* [ ] Backpressure control on execution engine

---

# 🧱 6. INFRASTRUCTURE RELIABILITY

### Process management

* [ ] Supervisor system (systemd / custom orchestrator)
* [ ] Auto-healing system for crashed containers/processes
* [ ] Health checks per terminal

---

### Observability

* [ ] Real-time logs per MT instance
* [ ] Centralized log aggregation
* [ ] Metrics per:

  * CPU per terminal
  * memory per terminal
  * execution latency
  * trade success/failure rate

---

### Alerting

* [ ] Alerts for:

  * terminal crash
  * broker disconnect
  * order failure spike
  * memory leak detection
  * latency spike

---

# 💾 7. DATA CONSISTENCY & STATE MANAGEMENT

### Trade state integrity

* [ ] Single source of truth for positions
* [ ] Broker vs system reconciliation loop
* [ ] No “ghost positions”

---

### Persistence layer

* [ ] All trades logged immutably
* [ ] Replay capability (audit + debugging)
* [ ] Recovery after full system restart

---

# 🧯 8. FAILURE RECOVERY SYSTEM (MOST IMPORTANT)

This is what separates production systems from hobby systems.

### Crash recovery

* [ ] Full system restart recovery (all terminals restored)
* [ ] Partial system recovery (only failed nodes restart)
* [ ] No manual repair required for normal failures

---

### Disaster scenarios

* [ ] VPS reboot recovery tested
* [ ] Network outage recovery tested
* [ ] Broker outage recovery tested
* [ ] Corrupted terminal recovery tested

---

# 🔐 9. SECURITY & ISOLATION

### Credential security

* [ ] MT credentials encrypted at rest
* [ ] No plain-text broker credentials in logs
* [ ] Secure secret rotation capability

---

### Tenant isolation

* [ ] Users cannot interfere with each other’s terminals
* [ ] No cross-user data leakage
* [ ] No shared execution state

---

# 🧪 10. TESTING & SIMULATION (CRITICAL BEFORE GOING LIVE)

You MUST simulate real stress:

### Load testing

* [ ] 10 → 50 → 100 MT terminals simulation
* [ ] Market open spike simulation
* [ ] News event volatility simulation

---

### Chaos testing

* [ ] Kill random MT terminals
* [ ] Simulate broker disconnection
* [ ] Simulate CPU starvation
* [ ] Simulate memory exhaustion

---

### Recovery testing

* [ ] Full VPS reboot test
* [ ] Docker restart test
* [ ] Network cut test

---

# 🧭 FINAL REALITY CHECK

If even ONE of these is weak:

```text id="k9z1aa"
your system will fail under real trading conditions
```

Not because your code is bad —
but because MT + Wine + real brokers are inherently unstable systems.

---

# 🧠 SIMPLE WAY TO THINK ABOUT IT

Before self-hosting, your system must be able to answer YES to:

> “Can this system survive chaos without human intervention?”

If the answer is not YES, then MetaApi is still the safer choice.

---