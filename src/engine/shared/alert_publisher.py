"""Engine -> gateway alert event bridge.

The gateway runs a Redis pub/sub subscriber (
``src/alert/redis/transport.go::Transport.subscribeLoop``) that receives
events on the ``etradie:alerts`` channel, deserialises them, and fans
them out to the affected user's WebSocket via the in-process alert Hub.

This module is the engine-side publisher for that channel. It exists
so the Python engine can surface events to the SPA using the SAME
wire shape and SAME transport the Go services already use; the SPA's
``RealtimeProvider`` and per-event-type modal handlers do not need to
know which service produced an event.

Wire-shape contract:

    {
        "id":        "20060102150405-<8 hex chars>",
        "source":    "<EventSource enum value>",
        "type":      "<TYPE constant>",
        "severity":  "<EventSeverity enum value>",
        "timestamp": "<RFC3339Nano UTC>",
        "user_id":   "<optional, omitted when empty>",
        "message":   "<short user-facing string>",
        "details":   { ... optional structured fields ... }
    }

The ID format matches the Go-side generator at
``src/alert/event.go::generateEventID``. The 14-digit timestamp prefix
is required so the gateway's ``RecentSince`` history-catchup path can
filter on it; using a different format would silently break the
event-id-since pagination in mixed-publisher deployments.

The channel name (``etradie:alerts``) is a wire-protocol contract, not
a deployment knob. Hard-coded on both ends so a typo at deploy time
cannot silently silence the cross-service bus.

Audit ref: ADMIN-QUOTA-9.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from engine.shared.cache.redis_cache import RedisCache
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Wire-protocol constants
# ---------------------------------------------------------------------------

# Redis pub/sub channel the gateway's alertredis.Transport subscribes
# to. MUST stay in lock-step with src/alert/redis/transport.go::defaultChannel.
ALERT_CHANNEL = "etradie:alerts"

# EventSource values. MUST match src/alert/event.go::EventSource
# constants EXACTLY (uppercase). The Go enum defines only four values:
# GATEWAY / EXECUTION / TRADE_MANAGER / SYSTEM. The engine is a backend
# system component without its own EventSource entry, so it publishes
# under SYSTEM. A lowercase "engine" string (the previous value) was a
# wire-protocol violation that any future source-based filter / UI
# would silently misclassify.
#
# Audit ref: ADMIN-QUOTA-AUDIT-V2-1.
SOURCE_ENGINE = "SYSTEM"

# EventSeverity values. MUST match src/alert/event.go::EventSeverity
# constants EXACTLY (uppercase). The SPA's RealtimeProvider checks
# `event.severity === 'WARNING'`; lowercase would silently break the
# generic-toast fallback for any future event type without a
# dedicated modal.
SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_ERROR = "ERROR"
SEVERITY_CRITICAL = "CRITICAL"

# Event type constants. Mirrors src/alert/event.go type-name constants.
# Add new constants here whenever a new constant lands on the Go side.
TYPE_LLM_PROVIDER_QUOTA_EXCEEDED = "LLM_PROVIDER_QUOTA_EXCEEDED"

# Maximum length of the provider error message included in event details.
# Matches the Go side's comment block byte-budget for the same field
# (src/alert/event.go::TypeLLMProviderQuotaExceeded). A verbose provider
# SDK trace cannot blow the WebSocket frame size budget.
_PROVIDER_DETAIL_MAX_CHARS = 256


# ---------------------------------------------------------------------------
# Event ID generator (byte-compatible with src/alert/event.go::generateEventID)
# ---------------------------------------------------------------------------


def _generate_event_id() -> str:
    """Return an event ID matching the Go-side format.

    Go reference (alert/event.go::generateEventID):
        return now.Format("20060102150405") + "-" + hex.EncodeToString(b)
    where b is 4 random bytes (8 hex chars).

    Keeping the exact format matters because the gateway's RecentSince
    parses the 14-digit prefix to filter Redis history by score; using
    any other format silently breaks history-catchup pagination for
    every event this publisher emits.
    """
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(4)
    return f"{now}-{suffix}"


def _rfc3339_nano_utc() -> str:
    """Return an RFC3339Nano UTC timestamp the Go side can parse cleanly.

    Python's isoformat() yields the right shape with microsecond
    precision; Go's time.RFC3339Nano accepts microsecond-precision
    timestamps without complaint (the "Nano" name is a Go convention,
    not a width requirement).
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------


class AlertPublisher:
    """Thin facade over RedisCache.publish() that enforces the wire shape.

    The class is intentionally stateless beyond the injected cache + the
    default source label. Callers do not pass severity / timestamp / id
    because those are intrinsics of the shape; passing them in would
    invite drift between event sites.
    """

    def __init__(
        self,
        cache: RedisCache,
        *,
        source: str = SOURCE_ENGINE,
        channel: str = ALERT_CHANNEL,
    ) -> None:
        self._cache = cache
        self._source = source
        self._channel = channel

    @property
    def channel(self) -> str:
        """Return the Redis channel this publisher writes to."""
        return self._channel

    async def publish(
        self,
        *,
        event_type: str,
        severity: str,
        message: str,
        user_id: str = "",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Emit one event on the alert channel.

        Errors during publish are logged and swallowed so the caller's
        primary control flow (e.g. raising a ProcessorError) is never
        derailed by a transient Redis failure. The event is best-effort
        cross-process notification, not a correctness boundary.
        """
        envelope: dict[str, Any] = {
            "id": _generate_event_id(),
            "source": self._source,
            "type": event_type,
            "severity": severity,
            "timestamp": _rfc3339_nano_utc(),
            "message": message,
        }
        if user_id:
            envelope["user_id"] = user_id
        if details:
            envelope["details"] = details

        try:
            await self._cache.publish(self._channel, envelope)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "alert_publish_failed",
                extra={
                    "channel": self._channel,
                    "event_type": event_type,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )

    async def publish_llm_provider_quota_exceeded(
        self,
        *,
        user_id: str,
        provider: str,
        model: str,
        detail: str,
        code: str,
    ) -> None:
        """Emit LLM_PROVIDER_QUOTA_EXCEEDED for a BYOK user.

        Fired by ``engine.processor.service.AnalysisProcessor`` after
        all LLM retries have been exhausted AND the classified failure
        is provider-quota / provider-rate-limit AND the active config
        is NOT on the platform key (BYOK only -- platform-key users
        are handled by the gateway's LLM_QUOTA_EXCEEDED event).

        The SPA listens for this event type and opens the dedicated
        provider-quota modal whose copy directs the user to their
        OWN provider's dashboard.

        Args:
            user_id: The authenticated user. Required so the gateway's
                Hub fans the event out only to that user's WS clients.
            provider: Canonical provider name (anthropic / openai /
                gemini / self_hosted / unknown).
            model: The configured model name that the call targeted.
            detail: Provider's raw error message. Truncated to
                ``_PROVIDER_DETAIL_MAX_CHARS`` so a verbose SDK trace
                cannot blow the WS frame budget.
            code: Classifier code (quota_exceeded | rate_limited).
                Lets the SPA distinguish "top up" remediation from
                "wait a moment" remediation in the modal copy.
        """
        if not user_id:
            # Defensive guard: an empty user_id would broadcast a
            # private modal trigger to every connected WS client. Refuse
            # to publish and log so the upstream call-site bug is
            # immediately visible.
            logger.warning(
                "alert_publish_provider_quota_skipped_no_user_id",
                extra={"provider": provider, "model": model, "code": code},
            )
            return

        truncated_detail = (detail or "")[:_PROVIDER_DETAIL_MAX_CHARS]
        await self.publish(
            event_type=TYPE_LLM_PROVIDER_QUOTA_EXCEEDED,
            severity=SEVERITY_WARNING,
            message="Your AI provider has reached its usage limit.",
            user_id=user_id,
            details={
                "provider": provider or "unknown",
                "model": model or "unknown",
                "detail": truncated_detail,
                "code": code or "",
            },
        )


# ---------------------------------------------------------------------------
# Optional module-level convenience: an env-driven channel override.
# ---------------------------------------------------------------------------


def channel_from_env(default: str = ALERT_CHANNEL) -> str:
    """Return the alert channel name, optionally overridden by env.

    The override exists for integration tests that need to isolate
    publishers per test run. Production MUST leave
    ``ALERT_CHANNEL_OVERRIDE`` unset so the wire contract with the
    gateway holds.
    """
    override = os.getenv("ALERT_CHANNEL_OVERRIDE", "").strip()
    return override or default
