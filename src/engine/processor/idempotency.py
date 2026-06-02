"""Idempotency guard for the analysis LLM call.

A single ``POST /api/v1/cycle/run`` can result in more than one
top-level ``AnalysisProcessor.process()`` call -- a proxy that abandons
and replays the request, or two analysis cycles triggered close
together. Each such duplicate re-runs the expensive, money-spending LLM
call on byte-identical input. This module collapses those duplicates
into a single LLM call using the shared Redis cache.

The dedupe identity is ``sha256(user_id : symbol : prompt_hash)``. Two
duplicate cycles for the same input produce the *same* ``prompt_hash``
(the system prompt + user message are byte-identical), so the digest is
stable across duplicates while remaining unique per distinct analysis.

Design (single-flight + result cache):

  1. ``check_cached`` -- if a completed ``ProcessorOutput`` is already
     cached for this digest, return it. No LLM call.
  2. ``acquire`` -- atomic ``SET key token NX EX ttl`` (single-flight).
     The first caller owns the lock and runs the real LLM call; a
     concurrent identical caller gets ``DUPLICATE`` and must NOT run the
     LLM call -- it polls the result key via ``await_result`` and
     returns the owner's output, or raises if none appears.
  3. ``store_result`` -- the owner persists its successful output under
     the result key (short TTL) so any in-flight or near-future
     duplicate returns it instead of re-billing the LLM.
  4. ``release`` -- the owner frees the lock (compare-and-delete).

Every operation FAILS OPEN: if Redis is unavailable the guard degrades
to "no deduplication" rather than blocking or failing the analysis. A
cache outage must never break a real user analysis.

Only SUCCESSFUL outputs are cached. Callers must never call
``store_result`` for an error / truncation / no-decision-yet state.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from engine.shared.logging import get_logger
from engine.processor.models.io import ProcessorOutput

logger = get_logger(__name__)

# Redis namespace for both the single-flight lock and the result cache.
# Validated by RedisCache._validate_namespace (alphanumeric + '_'/'-').
_NAMESPACE = "proc_idem"

# Lock TTL must cover the worst-case end-to-end processor call so the
# lock never expires while the owner is still streaming the LLM
# response (which would let a duplicate acquire it and start a second
# LLM call). Sized above CycleTimeoutSeconds (450s) + margin; the owner
# always releases explicitly on completion, so this is only a safety
# net against an owner that crashes mid-call.
_LOCK_TTL_SECONDS = 600

# Result-cache TTL. Long enough to absorb a duplicate that arrives
# shortly after the first call completes (the observed gap was ~64ms,
# but a slow proxy retry could be tens of seconds), short enough that a
# genuinely new user trigger minutes later is never served a stale
# decision. A fresh manual re-run produces a new analysis_id anyway.
_RESULT_TTL_SECONDS = 120

# When a duplicate finds the lock held, it polls the result key for up
# to this long before giving up. Bounded so a duplicate never hangs the
# request indefinitely waiting on a wedged owner.
_AWAIT_TIMEOUT_SECONDS = 5.0
_AWAIT_POLL_INTERVAL_SECONDS = 0.25


def compute_digest(*, user_id: str, symbol: str, prompt_hash: str) -> str:
    """Return the stable dedupe digest for an analysis call."""
    raw = f"{user_id}:{symbol}:{prompt_hash}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _lock_key(digest: str) -> str:
    return f"lock:{digest}"


def _result_key(digest: str) -> str:
    return f"result:{digest}"


@dataclass(frozen=True)
class LockHandle:
    """Proof of single-flight ownership for a given digest.

    ``token`` is the per-acquire nonce passed to ``release_lock`` so a
    slow owner can only delete a lock it still holds (never one that
    has expired and been re-acquired by a different caller).
    """

    digest: str
    token: str


class ProcessorIdempotency:
    """Redis-backed idempotency guard. Stateless beyond the injected cache."""

    def __init__(self, cache) -> None:
        # cache is an engine.shared.cache.redis_cache.RedisCache. Typed as
        # Any-ish here to avoid an import cycle with the container wiring;
        # only get/set/try_acquire_lock/release_lock are used.
        self._cache = cache

    async def check_cached(
        self, digest: str, *, trace_id: Optional[str] = None
    ) -> Optional[ProcessorOutput]:
        """Return a cached ProcessorOutput for this digest, or None.

        Fails open: any cache error returns None (treat as a miss).
        """
        try:
            raw = await self._cache.get(
                _NAMESPACE, _result_key(digest), trace_id=trace_id
            )
        except Exception as exc:  # noqa: BLE001 - fail open on any cache error
            logger.warning(
                "processor_idempotency_get_failed",
                extra={"digest": digest, "error": str(exc), "trace_id": trace_id},
            )
            return None
        if not isinstance(raw, dict):
            return None
        try:
            return ProcessorOutput(**raw)
        except Exception as exc:  # noqa: BLE001 - corrupt payload -> miss
            logger.warning(
                "processor_idempotency_decode_failed",
                extra={"digest": digest, "error": str(exc), "trace_id": trace_id},
            )
            return None

    async def acquire(
        self, digest: str, *, trace_id: Optional[str] = None
    ) -> Optional[LockHandle]:
        """Try to become the single in-flight owner for this digest.

        Returns a LockHandle when this caller owns the lock (it must run
        the real LLM call, then store_result + release). Returns None
        when another identical call already holds the lock -- the caller
        must NOT run the LLM call and should use await_result instead.

        Fails open: if Redis is unavailable, try_acquire_lock returns
        False; we surface that as "not owner" only when a result is
        already cached, otherwise as owner so the analysis still runs.
        To keep the fail-open posture explicit and race-free, callers
        invoke check_cached() first; here a False from a healthy Redis
        means a real concurrent owner exists.
        """
        token = uuid.uuid4().hex
        try:
            acquired = await self._cache.try_acquire_lock(
                _NAMESPACE, _lock_key(digest), token, _LOCK_TTL_SECONDS
            )
        except Exception as exc:  # noqa: BLE001 - fail open: run the analysis
            logger.warning(
                "processor_idempotency_lock_failed_failing_open",
                extra={"digest": digest, "error": str(exc), "trace_id": trace_id},
            )
            return LockHandle(digest=digest, token=token)
        if acquired:
            return LockHandle(digest=digest, token=token)
        return None

    async def await_result(
        self, digest: str, *, trace_id: Optional[str] = None
    ) -> Optional[ProcessorOutput]:
        """Poll the result key for a bounded window for the owner's output.

        Used by a duplicate caller that found the lock held. Returns the
        owner's ProcessorOutput once it lands, or None if the window
        elapses (owner still running, crashed, or produced a
        non-cacheable result such as an error).
        """
        deadline = time.monotonic() + _AWAIT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            cached = await self.check_cached(digest, trace_id=trace_id)
            if cached is not None:
                return cached
            await asyncio.sleep(_AWAIT_POLL_INTERVAL_SECONDS)
        return None

    async def store_result(
        self,
        digest: str,
        output: ProcessorOutput,
        *,
        trace_id: Optional[str] = None,
    ) -> None:
        """Cache a SUCCESSFUL ProcessorOutput for this digest.

        Best-effort: a cache write failure is logged and swallowed (the
        analysis already succeeded; failing to cache only forfeits
        deduplication for a late-arriving duplicate).
        """
        try:
            await self._cache.set(
                _NAMESPACE,
                _result_key(digest),
                output.model_dump(mode="json"),
                _RESULT_TTL_SECONDS,
                trace_id=trace_id,
            )
        except Exception as exc:  # noqa: BLE001 - best effort
            logger.warning(
                "processor_idempotency_store_failed",
                extra={"digest": digest, "error": str(exc), "trace_id": trace_id},
            )

    async def release(
        self, handle: LockHandle, *, trace_id: Optional[str] = None
    ) -> None:
        """Release the single-flight lock (compare-and-delete by token).

        Best-effort: a failed release just means the lock lingers until
        its TTL, which is harmless because the result is already cached.
        """
        try:
            await self._cache.release_lock(
                _NAMESPACE, _lock_key(handle.digest), handle.token
            )
        except Exception as exc:  # noqa: BLE001 - best effort
            logger.warning(
                "processor_idempotency_release_failed",
                extra={
                    "digest": handle.digest,
                    "error": str(exc),
                    "trace_id": trace_id,
                },
            )
