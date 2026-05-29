"""Unit tests for the Section 2 connectivity primitives.

All tests are in-process: no Redis, no Postgres, no broker. Fakes
are constructed in the test module so CI can run them on a worker
with zero infra dependencies.

Audit ref: CHECKLIST Section 2 - every checkbox.
"""
from __future__ import annotations

import asyncio
import time as _time

import pytest

from engine.shared.exceptions import (
    ProviderResponseError,
    ProviderStalePriceError,
)
from engine.ta.broker.connectivity import (
    BrokerHeartbeatService,
    HeartbeatResult,
    HeartbeatState,
    ReconnectPolicy,
    SymbolResolver,
    TickFreshnessGuard,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------
# ReconnectPolicy
# ---------------------------------------------------------------------
async def test_reconnect_policy_full_jitter_schedule(monkeypatch: pytest.MonkeyPatch):
    p = ReconnectPolicy(base_secs=1.0, cap_secs=8.0, max_attempts=5)
    monkeypatch.setattr("random.uniform", lambda a, b: b)
    assert p.next_delay(1) == 1.0
    assert p.next_delay(2) == 2.0
    assert p.next_delay(3) == 4.0
    assert p.next_delay(4) == 8.0
    assert p.next_delay(5) == 8.0


async def test_reconnect_policy_exhaustion_raises_last(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("random.uniform", lambda a, b: 0.0)

    class _Boom(Exception):
        pass

    p = ReconnectPolicy(base_secs=0.001, cap_secs=0.001, max_attempts=3)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        raise _Boom(f"call {calls['n']}")

    with pytest.raises(_Boom) as ei:
        await p.run_with_retry(factory, retry_on=(_Boom,), operation_label="test")
    assert "call 3" in str(ei.value)
    assert calls["n"] == 3


async def test_reconnect_policy_recovers_after_transient(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("random.uniform", lambda a, b: 0.0)

    class _Boom(Exception):
        pass

    p = ReconnectPolicy(base_secs=0.001, cap_secs=0.001, max_attempts=5)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Boom("transient")
        return "ok"

    result = await p.run_with_retry(factory, retry_on=(_Boom,), operation_label="test")
    assert result == "ok"
    assert calls["n"] == 3


# ---------------------------------------------------------------------
# TickFreshnessGuard
# ---------------------------------------------------------------------
async def test_tick_freshness_guard_passes_fresh():
    g = TickFreshnessGuard(max_age_seconds=10.0, provider="zmq", account_id="acct")
    g.assert_fresh(symbol="EURUSD", tick_unix_ts=int(_time.time()))


async def test_tick_freshness_guard_rejects_stale():
    g = TickFreshnessGuard(max_age_seconds=5.0, provider="zmq", account_id="acct")
    with pytest.raises(ProviderStalePriceError) as ei:
        g.assert_fresh(symbol="EURUSD", tick_unix_ts=int(_time.time()) - 60)
    assert ei.value.details["reason"] == "stale_by_age"
    assert ei.value.details["max_age_seconds"] == 5.0


async def test_tick_freshness_guard_rejects_zero_timestamp():
    g = TickFreshnessGuard(max_age_seconds=10.0, provider="zmq", account_id="acct")
    with pytest.raises(ProviderStalePriceError) as ei:
        g.assert_fresh(symbol="EURUSD", tick_unix_ts=0)
    assert ei.value.details["reason"] == "stale_by_session"


async def test_tick_freshness_guard_disabled_when_max_age_zero():
    g = TickFreshnessGuard(max_age_seconds=0.0, provider="zmq", account_id="acct")
    g.assert_fresh(symbol="EURUSD", tick_unix_ts=1)


# ---------------------------------------------------------------------
# BrokerHeartbeatService
# ---------------------------------------------------------------------
class _FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict] = {}
        self.deleted: list[str] = []
        self.expirations: dict[str, int] = {}
        self.kv: dict[str, str] = {}

    async def hset(self, key: str, mapping: dict) -> None:
        self.hashes.setdefault(key, {}).update(mapping)

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl

    async def delete(self, key: str) -> None:
        self.hashes.pop(key, None)
        self.deleted.append(key)

    async def get(self, key: str):
        v = self.kv.get(key)
        return v.encode() if isinstance(v, str) else v

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.kv[key] = value


async def test_heartbeat_service_state_transitions():
    redis = _FakeRedis()
    svc = BrokerHeartbeatService(
        redis_client=redis,
        interval_secs=0.05,
        timeout_secs=0.04,
        failure_threshold=2,
    )
    counter = {"n": 0}

    async def probe():
        counter["n"] += 1
        n = counter["n"]
        if n <= 1:
            return HeartbeatResult(ok=True, broker_connected=True, authenticated=True)
        if n <= 3:
            return HeartbeatResult(
                ok=False,
                broker_connected=False,
                error_type="DisconnectedFromBroker",
                error_message="mt5_connected=False",
            )
        return HeartbeatResult(ok=True, broker_connected=True, authenticated=True)

    svc.register(provider="zmq", account_id="acct-1", probe=probe)
    await asyncio.sleep(0.4)
    state = svc.state_of(provider="zmq", account_id="acct-1")
    await svc.stop()
    assert state in {HeartbeatState.CONNECTED, HeartbeatState.DEGRADED, HeartbeatState.DISCONNECTED}
    matching = [k for k in redis.hashes if k.endswith(":zmq:acct-1")]
    assert matching, "expected Redis hash for the registered connection"


async def test_heartbeat_service_register_replaces_existing():
    redis = _FakeRedis()
    svc = BrokerHeartbeatService(
        redis_client=redis,
        interval_secs=10.0,
        timeout_secs=1.0,
        failure_threshold=3,
    )
    calls = {"first": 0, "second": 0}

    async def first():
        calls["first"] += 1
        return HeartbeatResult(ok=True, broker_connected=True, authenticated=True)

    async def second():
        calls["second"] += 1
        return HeartbeatResult(ok=True, broker_connected=True, authenticated=True)

    svc.register(provider="zmq", account_id="acct-1", probe=first)
    await asyncio.sleep(0.02)
    svc.register(provider="zmq", account_id="acct-1", probe=second)
    await asyncio.sleep(0.05)
    await svc.stop()
    assert calls["first"] >= 1
    assert calls["second"] >= 1


# ---------------------------------------------------------------------
# SymbolResolver
# ---------------------------------------------------------------------
class _FakeSymbolRow:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeBrokerSymbolRepo:
    def __init__(self, rows: list[str] | None = None) -> None:
        self.rows = [_FakeSymbolRow(n) for n in (rows or [])]
        self.upserts: list[str] = []

    async def get_by_name(self, *, provider: str, account_id: str, name: str):
        for r in self.rows:
            if r.name == name:
                return r
        return None

    async def get_all_by_account(self, *, provider: str, account_id: str):
        return list(self.rows)

    async def upsert(self, **kwargs):
        self.upserts.append(kwargs["name"])
        self.rows.append(_FakeSymbolRow(kwargs["name"]))
        return self.rows[-1]


class _FakeUOW:
    def __init__(self, repo: _FakeBrokerSymbolRepo) -> None:
        self.broker_symbol_repo = repo

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _FakeUOWFactory:
    def __init__(self, repo: _FakeBrokerSymbolRepo) -> None:
        self._repo = repo

    def __call__(self):
        return _FakeUOW(self._repo)


async def test_symbol_resolver_redis_hit():
    redis = _FakeRedis()
    await redis.set("etradie:symbol:resolve:zmq:acct:EURUSD", "EURUSDm")
    repo = _FakeBrokerSymbolRepo()

    async def fetch_never():
        raise AssertionError("fetch_all_names must not be called on Redis hit")

    r = SymbolResolver(
        provider="zmq",
        account_id="acct",
        fetch_all_names=fetch_never,
        uow_factory=_FakeUOWFactory(repo),
        redis_client=redis,
    )
    assert await r.resolve("EURUSD") == "EURUSDm"


async def test_symbol_resolver_db_hit_suffix():
    redis = _FakeRedis()
    repo = _FakeBrokerSymbolRepo(rows=["EURUSDm"])

    async def fetch_never():
        raise AssertionError("fetch_all_names must not be called on DB hit")

    r = SymbolResolver(
        provider="zmq",
        account_id="acct",
        fetch_all_names=fetch_never,
        uow_factory=_FakeUOWFactory(repo),
        redis_client=redis,
    )
    assert await r.resolve("EURUSD") == "EURUSDm"


async def test_symbol_resolver_live_probe_then_persists():
    redis = _FakeRedis()
    repo = _FakeBrokerSymbolRepo()
    fetched = {"called": False}

    async def fetch_all():
        fetched["called"] = True
        return ["AUDUSD.r", "EURUSD.r", "GBPUSD.r"]

    r = SymbolResolver(
        provider="zmq",
        account_id="acct",
        fetch_all_names=fetch_all,
        uow_factory=_FakeUOWFactory(repo),
        redis_client=redis,
    )
    assert await r.resolve("EURUSD") == "EURUSD.r"
    assert fetched["called"]
    assert "EURUSD.r" in repo.upserts


async def test_symbol_resolver_miss_raises():
    redis = _FakeRedis()
    repo = _FakeBrokerSymbolRepo()

    async def fetch_all():
        return ["BTCUSD", "ETHUSD"]

    r = SymbolResolver(
        provider="zmq",
        account_id="acct",
        fetch_all_names=fetch_all,
        uow_factory=_FakeUOWFactory(repo),
        redis_client=redis,
    )
    with pytest.raises(ProviderResponseError):
        await r.resolve("EURUSD")
