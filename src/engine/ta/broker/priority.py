"""Broker request priority tier.

Provides a process-wide, async-safe priority signal that broker clients can
read when deciding how to schedule themselves against shared rate-limited
resources (e.g. the MetaAPI per-account market-data semaphore).

Design
------
BrokerBase intentionally does not take a `priority` argument on every method
-- adding one would force every caller (TA orchestrator, signal extractors,
the Go execution and management bridges) to thread an enum through call sites
that have no opinion on scheduling. Instead we use ``contextvars.ContextVar``
so the priority is scoped to the async task that sets it and propagates into
any awaited callees automatically, without polluting any function signature.

Usage
-----
Foreground HTTP handlers do nothing -- the default priority is FOREGROUND, so
their broker calls are always served first.

Background pre-warm / revalidation tasks wrap their broker calls::

    async with broker_priority(BrokerRequestPriority.BACKGROUND):
        seq = await client.fetch_candles(...)

While that block is active *and only inside it*, MetaApiClient routes the
candles fetch through its background semaphore tier, which has fewer slots
than the foreground tier and cannot starve foreground requests.

Why a context manager not an argument
-------------------------------------
  * Zero changes to BrokerBase.fetch_candles signature -- preserves ZMQ,
    TwelveData, and every existing call site bit-for-bit.
  * Priority propagates through indirect call chains automatically (e.g.
    fetch_latest_candle -> fetch_candles inside the same client).
  * contextvars are async-safe: each asyncio.Task gets its own copy on
    creation, so a foreground task's priority is never accidentally seen
    by a sibling background task.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from contextvars import ContextVar
from enum import StrEnum, unique


@unique
class BrokerRequestPriority(StrEnum):
    """Scheduling tier for a broker request.

    FOREGROUND is the default. It models user-visible work where latency is
    a hard constraint -- a dashboard chart click, an order placement, a tick
    poll. Foreground requests acquire reserved capacity that background
    work cannot consume.

    BACKGROUND models opportunistic work that is purely a latency optimisation
    for some *future* foreground request -- typically the chart pre-warm
    pipeline or a stale-while-revalidate refresh. Background requests are
    bounded to a smaller share of the broker budget and must always yield
    to foreground requests when capacity is contended.
    """

    FOREGROUND = "foreground"
    BACKGROUND = "background"


_current_priority: ContextVar[BrokerRequestPriority] = ContextVar(
    "broker_request_priority",
    default=BrokerRequestPriority.FOREGROUND,
)


def get_priority() -> BrokerRequestPriority:
    """Return the priority active in the current async context.

    Defaults to FOREGROUND for any code path that has not explicitly entered
    a ``broker_priority`` block. This makes all existing callers (which know
    nothing about priority) behave exactly as before.
    """
    return _current_priority.get()


@contextlib.contextmanager
def broker_priority(priority: BrokerRequestPriority) -> Iterator[None]:
    """Set the broker request priority for the enclosed block.

    Restores the previous priority on exit even if the block raises.

    Example::

        async with broker_priority(BrokerRequestPriority.BACKGROUND):
            await client.fetch_candles(symbol=..., timeframe=..., count=...)
    """
    token = _current_priority.set(priority)
    try:
        yield
    finally:
        _current_priority.reset(token)
