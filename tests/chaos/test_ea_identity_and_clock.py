"""Unit tests for Section 4 EA identity + clock skew primitives.

All tests are pure in-process: no Redis, no Postgres, no broker.
The EA_IDENTITY and EA_CLOCK contracts are validated against the
shape ZmqClient sends + the EA returns.

Audit ref: CHECKLIST Section 4.
"""
from __future__ import annotations

import time as _time

import pytest

from engine.shared.exceptions import EAClockSkewError, EAIdentityMismatchError
from engine.ta.broker.mt5.clock_skew import ClockSkewMonitor, EAClockSample
from engine.ta.broker.mt5.ea_identity import (
    EAIdentitySnapshot,
    EAIdentityVerifier,
    ExpectedEAIdentity,
)


# ---------------------------------------------------------------------
# EAIdentityVerifier
# ---------------------------------------------------------------------
def _snap(**overrides):
    base = dict(
        magic_number=20260321,
        account_login="435112187",
        account_server="Exness-MT5Trial9",
        account_company="Exness",
        account_name="Test User",
        terminal_build=4200,
        ea_version="2.10.0",
        zmq_port=5555,
        started_at=int(_time.time()),
    )
    base.update(overrides)
    return EAIdentitySnapshot(**base)


def test_ea_identity_match_passes():
    v = EAIdentityVerifier(provider="zmq", account_id="acct-1")
    expected = ExpectedEAIdentity(
        magic_number=20260321,
        account_login="435112187",
        account_server="Exness-MT5Trial9",
        minimum_ea_version="2.10.0",
    )
    v.verify(_snap(), expected)  # must not raise


def test_ea_identity_magic_mismatch_raises():
    v = EAIdentityVerifier(provider="zmq", account_id="acct-1")
    expected = ExpectedEAIdentity(magic_number=20260321)
    with pytest.raises(EAIdentityMismatchError) as ei:
        v.verify(_snap(magic_number=99999), expected)
    assert "magic" in ei.value.details["mismatches"]
    assert ei.value.details["mismatches"]["magic"]["expected"] == 20260321
    assert ei.value.details["mismatches"]["magic"]["observed"] == 99999


def test_ea_identity_login_mismatch_raises():
    v = EAIdentityVerifier(provider="zmq", account_id="acct-1")
    expected = ExpectedEAIdentity(account_login="435112187")
    with pytest.raises(EAIdentityMismatchError) as ei:
        v.verify(_snap(account_login="WRONG"), expected)
    assert "login" in ei.value.details["mismatches"]


def test_ea_identity_server_mismatch_raises():
    v = EAIdentityVerifier(provider="zmq", account_id="acct-1")
    expected = ExpectedEAIdentity(account_server="Exness-MT5Trial9")
    with pytest.raises(EAIdentityMismatchError) as ei:
        v.verify(_snap(account_server="ICMarketsSC-Demo"), expected)
    assert "server" in ei.value.details["mismatches"]


def test_ea_identity_old_ea_version_raises():
    v = EAIdentityVerifier(provider="zmq", account_id="acct-1")
    expected = ExpectedEAIdentity(minimum_ea_version="2.10.0")
    with pytest.raises(EAIdentityMismatchError) as ei:
        v.verify(_snap(ea_version="2.0.0"), expected)
    assert "ea_version" in ei.value.details["mismatches"]


def test_ea_identity_zero_magic_means_any():
    v = EAIdentityVerifier(provider="zmq", account_id="acct-1")
    expected = ExpectedEAIdentity(magic_number=0)  # sentinel
    v.verify(_snap(magic_number=12345), expected)  # must not raise


# ---------------------------------------------------------------------
# ClockSkewMonitor
# ---------------------------------------------------------------------
def test_clock_skew_median_window():
    m = ClockSkewMonitor(
        provider="zmq",
        account_id="acct-1",
        window_size=5,
        max_acceptable_skew_secs=10.0,
    )
    now = 1_700_000_000
    samples = [
        EAClockSample(server_time=now - 2, ea_local_time=now - 2, tick_time=now - 2),
        EAClockSample(server_time=now - 4, ea_local_time=now - 4, tick_time=now - 4),
        EAClockSample(server_time=now - 3, ea_local_time=now - 3, tick_time=now - 3),
        EAClockSample(server_time=now - 3, ea_local_time=now - 3, tick_time=now - 3),
        EAClockSample(server_time=now - 5, ea_local_time=now - 5, tick_time=now - 5),
    ]
    skews = [m.sample(now, s) for s in samples]
    # median of [2, 4, 3, 3, 5] == 3
    assert skews[-1] == 3.0
    assert m.skew_seconds() == 3.0
    assert not m.is_degraded()


def test_clock_skew_degraded_above_threshold():
    m = ClockSkewMonitor(
        provider="zmq",
        account_id="acct-1",
        window_size=3,
        max_acceptable_skew_secs=1.0,
    )
    now = 1_700_000_000
    m.sample(now, EAClockSample(server_time=now - 5, ea_local_time=0, tick_time=0))
    m.sample(now, EAClockSample(server_time=now - 6, ea_local_time=0, tick_time=0))
    m.sample(now, EAClockSample(server_time=now - 7, ea_local_time=0, tick_time=0))
    assert m.is_degraded()
    with pytest.raises(EAClockSkewError):
        m.assert_within_tolerance()


def test_clock_skew_now_compensated_subtracts_skew():
    m = ClockSkewMonitor(
        provider="zmq",
        account_id="acct-1",
        window_size=3,
        max_acceptable_skew_secs=30.0,
    )
    now = 1_700_000_000
    m.sample(now, EAClockSample(server_time=now - 4, ea_local_time=0, tick_time=0))
    m.sample(now, EAClockSample(server_time=now - 4, ea_local_time=0, tick_time=0))
    m.sample(now, EAClockSample(server_time=now - 4, ea_local_time=0, tick_time=0))
    assert m.skew_seconds() == 4.0
    assert m.now_compensated(now) == now - 4


def test_clock_skew_zero_server_time_ignored():
    m = ClockSkewMonitor(
        provider="zmq",
        account_id="acct-1",
        window_size=3,
        max_acceptable_skew_secs=10.0,
    )
    # First sample has no server_time -> ignored; skew stays 0.
    assert m.sample(1_700_000_000, EAClockSample(server_time=0, ea_local_time=0, tick_time=0)) == 0.0
    assert m.skew_seconds() == 0.0
