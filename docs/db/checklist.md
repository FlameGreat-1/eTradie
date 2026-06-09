For a trading platform, the database is not just storage.

It is part of the **financial system of record**.

The database requirements for:

* a blog,
* e-commerce store,
* CRM,

are very different from:

* trade execution,
* account balances,
* positions,
* risk calculations,
* audit trails.

For a real-money trading platform, database engineering should be treated as a first-class system.

---

# 🔴 TIER 1: DATA CORRECTNESS

The most important requirement.

## Single Source of Truth

* [ ] One authoritative source for positions
* [ ] One authoritative source for accounts
* [ ] One authoritative source for orders
* [ ] One authoritative source for broker mappings

Never maintain competing truths.

---

## Referential Integrity

* [ ] Foreign keys enabled
* [ ] Cascading deletes carefully controlled
* [ ] Orphan records impossible
* [ ] Data relationships enforced by DB

Examples:

```text
users
  └── trading_accounts
         └── positions
                └── executions
```

must always remain valid.

---

## Constraints

* [ ] NOT NULL constraints
* [ ] CHECK constraints
* [ ] ENUM constraints
* [ ] Unique constraints

Examples:

```sql
volume > 0
```

```sql
status IN (...)
```

```sql
unique(order_id)
```

---

# 🔴 TIER 2: ACID COMPLIANCE

Critical.

Your database should guarantee:

### Atomicity

* [ ] Entire transaction succeeds
* [ ] Entire transaction fails

Never partial success.

---

### Consistency

* [ ] Constraints always valid
* [ ] State transitions valid
* [ ] Business invariants preserved

---

### Isolation

* [ ] Concurrent transactions safe
* [ ] Race conditions prevented

---

### Durability

* [ ] Committed trades survive crashes
* [ ] WAL enabled
* [ ] Recovery tested

---

# 🔴 TIER 3: TRANSACTION DESIGN

Many trading bugs originate here.

---

## Transaction Boundaries

For example:

Trade Execution

```text
Create Order
Create Audit Entry
Update Position
Update Account State
```

Should be:

```text
ONE TRANSACTION
```

not four independent writes.

---

## Rollback Capability

* [ ] Failed transactions rollback completely
* [ ] Automatic rollback handling
* [ ] Partial updates impossible

---

## Idempotent Writes

* [ ] Duplicate execution requests safe
* [ ] Retry-safe transactions
* [ ] Unique execution IDs

---

# 🔴 TIER 4: CONCURRENCY CONTROL

Huge for trading.

---

## Row Locking

Use:

```sql
SELECT ... FOR UPDATE
```

when appropriate.

---

## Race Condition Protection

Prevent:

```text
Two execution workers
opening same trade twice
```

---

## Deadlock Strategy

* [ ] Deadlock detection
* [ ] Deadlock retry strategy
* [ ] Consistent lock ordering

---

# 🔴 TIER 5: PERFORMANCE

---

## Indexing

Audit every query.

* [ ] Primary keys indexed
* [ ] Foreign keys indexed
* [ ] Frequent lookups indexed
* [ ] Composite indexes reviewed

---

## Query Analysis

* [ ] EXPLAIN plans reviewed
* [ ] Slow query logging enabled
* [ ] Full table scans identified

---

## Pagination

Never:

```sql
SELECT * FROM executions
```

for large datasets.

---

Use:

* [ ] Cursor pagination
* [ ] Keyset pagination

---

# 🔴 TIER 6: SECURITY

---

## SQL Injection Protection

* [ ] Parameterized queries only
* [ ] Prepared statements only
* [ ] No string concatenation SQL

---

Bad:

```sql
SELECT * FROM users WHERE id = '$id'
```

Good:

```sql
SELECT * FROM users WHERE id = $1
```

---

## Database Permissions

* [ ] Separate DB users per service
* [ ] Least privilege
* [ ] No application superuser

---

Example:

Execution Service:

```text
read/write executions
```

NOT:

```text
DROP DATABASE
```

---

# 🔴 TIER 7: AUDITABILITY

For financial systems:

Every important change must be traceable.

---

## Audit Tables

Track:

* [ ] Order creation
* [ ] Order modification
* [ ] Order cancellation
* [ ] Account updates
* [ ] Risk changes

---

## Immutable Audit Logs

* [ ] Append-only
* [ ] No updates
* [ ] No deletes

---

## Change Attribution

Store:

* [ ] user_id
* [ ] service_id
* [ ] request_id
* [ ] timestamp

---

# 🔴 TIER 8: RECOVERY

Extremely important.

---

## Backup Strategy

* [ ] Daily backups
* [ ] Incremental backups
* [ ] Automated backups

---

## Restore Testing

Most companies backup.

Few test restores.

* [ ] Monthly restore drills
* [ ] Restore documentation
* [ ] Recovery runbooks

---

## Point-in-Time Recovery

* [ ] WAL archiving
* [ ] PITR tested

---

# 🔴 TIER 9: REPLICATION

---

## High Availability

* [ ] Primary database
* [ ] Standby replica
* [ ] Automatic failover strategy

---

## Read Replicas

Use for:

* [ ] dashboards
* [ ] analytics
* [ ] reporting

Never for critical trade writes.

---

# 🔴 TIER 10: OBSERVABILITY

Monitor continuously.

---

## Database Metrics

* [ ] Connection count
* [ ] Active transactions
* [ ] Deadlocks
* [ ] Replication lag
* [ ] Cache hit ratio
* [ ] Query latency

---

## Alerts

Immediate alerts for:

* [ ] High latency
* [ ] Replication failure
* [ ] Backup failure
* [ ] Disk nearing capacity

---

# 🔴 TIER 11: FAILURE MODES

Design for failure.

---

## Power Loss

* [ ] Recovery tested

---

## VPS Reboot

* [ ] Recovery tested

---

## Database Crash

* [ ] Recovery tested

---

## Corrupted Index

* [ ] Detection procedures
* [ ] Recovery procedures

---

## Full Disk

* [ ] Alerting
* [ ] Mitigation procedures

---

# 🔴 TIER 12: TRADING-SPECIFIC DATABASE REQUIREMENTS

This is where many systems fail.

---

## Order State Machine

Enforce valid transitions.

Example:

```text
PENDING
→ SUBMITTED
→ FILLED
```

Not:

```text
FILLED
→ PENDING
```

---

## Idempotency Table

* [ ] Execution IDs unique
* [ ] Duplicate request detection

---

## Reconciliation Support

Store:

* [ ] broker ticket
* [ ] broker position id
* [ ] broker account id

to support recovery and reconciliation.

---

## Event Sourcing (Recommended)

For critical actions:

Store events:

```text
ORDER_CREATED
ORDER_SUBMITTED
ORDER_FILLED
POSITION_CLOSED
```

This makes reconstruction possible after failures.

---

# 🔴 TIER 13: POSTGRESQL-SPECIFIC BEST PRACTICES

Since most systems like yours use PostgreSQL:

* [ ] WAL enabled
* [ ] PITR enabled
* [ ] Autovacuum monitored
* [ ] Connection pooling (e.g. PgBouncer)
* [ ] Partition large tables
* [ ] Monitor bloat
* [ ] Tune shared_buffers
* [ ] Tune work_mem
* [ ] Tune effective_cache_size

---

# 🚨 THE 10 THINGS I WOULD REFUSE TO GO LIVE WITHOUT

1. ACID transactions
2. Foreign keys + constraints
3. Parameterized queries only
4. Unique execution IDs
5. Rollback-tested transaction flows
6. Automated backups
7. Restore-tested backups
8. Audit logging
9. Reconciliation support
10. Point-in-time recovery

If those ten are implemented correctly, we've covered the majority of catastrophic database failure modes that affect real-money trading platforms. The next level beyond that is high availability, replication, and disaster recovery engineering.
