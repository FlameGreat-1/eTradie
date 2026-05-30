"""Chart data endpoints (Dashboard TradingView chart).

These public-facing endpoints power the dashboard's Lightweight Charts.
/api/broker/candles provides historical OHLCV data for the initial
chart render, and /api/broker/stream-ticks provides a true WebSocket
stream of live tick prices for real-time chart animation.

Routes:
    GET /api/broker/symbols
    GET /api/broker/candles
    WS  /api/broker/stream-ticks
    WS  /api/broker/stream-positions
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time as _time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect

from engine.dependencies import Container
from engine.helpers import _resolve_user_broker
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.logging import get_logger
from engine.ta.broker.priority import BrokerRequestPriority, broker_priority
from engine.ta.constants import Timeframe as TF

logger = get_logger(__name__)
router = APIRouter()

# ── Broker Symbol Directory ────────────────────────────────────────
# Fetches the entire list of available instruments from the connected
# broker (Market Watch for ZMQ, or the MetaApi /symbols endpoint).
# Cached in-memory keyed by (user_id, provider, account_id) so a
# multi-tenant deployment cannot serve user A's symbols to user B.
# The triple-key matches the scope BrokerSymbolRepository uses for
# its persistent index, so the cache and the registry never disagree
# on identity.
#
# Capacity-bounded (1024 entries) with FIFO eviction on overflow so a
# high-tenant cluster cannot leak memory through this cache. Per-entry
# TTL is short (10s on cold path) because BrokerSyncService refreshes
# the persistent broker_symbols table in the background; this cache
# is only a hot-path shield against repeated DB reads during a single
# dashboard render.
from collections import OrderedDict

_BROKER_SYMBOLS_CACHE_CAPACITY: int = 1024
_broker_symbols_cache: "OrderedDict[tuple[str, str, str], tuple[dict, float]]" = OrderedDict()


def _broker_symbols_cache_get(
    key: tuple[str, str, str], *, now: float,
) -> dict | None:
    """Return the cached payload for `key` if still fresh, else None.

    Touches the entry's LRU position so frequently-accessed users
    survive eviction longer than cold ones.
    """
    entry = _broker_symbols_cache.get(key)
    if entry is None:
        return None
    payload, expires_at = entry
    if now >= expires_at:
        # Stale; remove eagerly so subsequent lookups do not pay the
        # tuple-unpack cost on a known-bad entry.
        _broker_symbols_cache.pop(key, None)
        return None
    # Touch LRU position (move_to_end is O(1) on OrderedDict).
    _broker_symbols_cache.move_to_end(key)
    return payload


def _broker_symbols_cache_set(
    key: tuple[str, str, str],
    payload: dict,
    *,
    now: float,
    ttl_seconds: float,
) -> None:
    """Insert `payload` under `key`; evict the oldest entry when full."""
    expires_at = now + ttl_seconds
    if key in _broker_symbols_cache:
        _broker_symbols_cache.move_to_end(key)
    _broker_symbols_cache[key] = (payload, expires_at)
    # FIFO-on-overflow eviction. popitem(last=False) drops the
    # oldest-inserted entry (which is also the least-recently-touched
    # because every get() and set() moves to the end).
    while len(_broker_symbols_cache) > _BROKER_SYMBOLS_CACHE_CAPACITY:
        _broker_symbols_cache.popitem(last=False)


@router.get("/api/broker/symbols")
async def broker_symbols(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Return all available broker instruments with name, description, and path.

    Reads from the persistent BrokerSymbolRegistry for maximum performance
    and full metadata. Triggers background sync if registry is empty.
    """
    from engine.ta.broker.sync import BrokerSyncService

    container = request.app.state.container

    # Resolve the user's broker client first so we can build the
    # cache key. Without the client we cannot know which (provider,
    # account_id) tuple this user's symbols belong to.
    broker_client = await _resolve_user_broker(container, user.user_id)
    if not broker_client:
         raise HTTPException(status_code=503, detail="No active broker connection")

    cache_key = (
        user.user_id,
        broker_client.provider_name,
        broker_client.account_id,
    )
    now = _time.time()
    cached = _broker_symbols_cache_get(cache_key, now=now)
    if cached is not None:
        return cached

    ta_uow_factory = container.ta_uow_factory

    try:
        async with ta_uow_factory() as uow:
            # 1. Fetch from persistent registry (Ordered by name for UI consistency)
            db_symbols = await uow.broker_symbol_repo.get_all_by_account(
                provider=broker_client.provider_name,
                account_id=broker_client.account_id
            )

            # 2. If registry is empty, trigger an immediate sync and return names as fallback
            if not db_symbols:
                logger.info(
                    "broker_registry_empty_triggering_initial_sync",
                    extra={"user_id": user.user_id}
                )
                sync_service = BrokerSyncService(broker_client, ta_uow_factory)
                # Dispatch background task
                asyncio.create_task(sync_service.sync_all_symbols())

                # Fallback to fast broker call (names only) for initial display
                try:
                    raw_names = await broker_client.get_all_symbol_names()
                    symbols = [{"name": n, "description": n, "path": n} for n in raw_names]
                except Exception:
                    # If even the fallback fails, return an empty list instead of crashing the UI
                    symbols = []
            else:
                # Map DB records to the frontend schema, sorted by name
                symbols = [
                    {
                        "name": s.name,
                        "description": s.description or s.name,
                        "path": s.path or s.name,
                        "digits": s.digits,
                        "point": s.point
                    }
                    for s in sorted(db_symbols, key=lambda x: x.name)
                ]

        result = {"symbols": symbols, "count": len(symbols)}
        _broker_symbols_cache_set(
            cache_key, result, now=now, ttl_seconds=10.0,
        )
        return result

    except Exception as exc:
        logger.error(
            "broker_symbols_failed",
            extra={"error": str(exc), "user_id": user.user_id},
        )
        raise HTTPException(status_code=502, detail=f"Failed to fetch broker symbols: {exc}")


# -- Timeframe map (shared by candles + pre-warm) --------------------------

_TF_MAP = {
    "M1": TF.M1, "M5": TF.M5, "M15": TF.M15, "M30": TF.M30,
    "H1": TF.H1, "H3": TF.H3, "H4": TF.H4,
    "H6": TF.H6, "H8": TF.H8, "H12": TF.H12,
    "D1": TF.D1, "W1": TF.W1, "MN1": TF.MN1,
}

# Full timeframe coverage for pre-warming.
_PREWARM_TIMEFRAMES = (
    "M1", "M5", "M15", "M30",
    "H1", "H3", "H4", "H6", "H8", "H12",
    "D1", "W1", "MN1",
)


@router.get("/api/broker/candles")
async def chart_candles(
    request: Request,
    symbol: str = Query(..., description="Broker symbol, e.g. USDJPYm"),
    timeframe: str = Query("H1", description="Timeframe: M1,M5,M15,M30,H1,H4,D1,W1"),
    count: int = Query(2000, ge=10, le=5000, description="Number of candles"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Return historical OHLCV candles for the dashboard chart.

    Implements an enterprise-grade Stale-While-Revalidate cache backed
    by Redis with single-flight upstream fetches, a hard deadline on
    the cold-miss path, and adjacent-timeframe pre-warming.
    """
    # -- Tunables -------------------------------------------------------
    REVALIDATE_AFTER_S = 30
    TOTAL_TTL_S = 1800
    COLD_FETCH_DEADLINE_S = 60
    LOCK_TTL_S = 90
    LOCK_WAIT_POLL_S = 0.15
    PREWARM_COOLDOWN_S = 300
    REVALIDATE_COOLDOWN_S = 20
    PREWARM_WAVE_DEADLINE_S = 300
    BACKGROUND_FETCH_DEADLINE_S = 25
    PREWARM_SPACING_S = 0.25

    tf_norm = timeframe.upper()
    tf = _TF_MAP.get(tf_norm)
    if tf is None:
        raise HTTPException(
            status_code=400, detail=f"Invalid timeframe: {timeframe}"
        )

    container: Container = request.app.state.container

    safe_symbol = symbol.replace(" ", "_")
    cache_key = f"{user.user_id}:{safe_symbol}:{tf_norm}:{count}"
    lock_key = f"lock:{cache_key}"
    prewarm_coord_key = f"prewarm:{user.user_id}:{safe_symbol}:{count}"
    revalidate_coord_key = f"revalidate:{cache_key}"

    async def _fetch_from_broker(
        target_tf: "TF",
        target_tf_label: str,
        *,
        background: bool,
    ) -> dict:
        """Authoritative broker fetch -> normalized payload."""
        client = await _resolve_user_broker(container, user.user_id)
        if background:
            with broker_priority(BrokerRequestPriority.BACKGROUND):
                seq = await client.fetch_candles(
                    symbol=symbol,
                    timeframe=target_tf,
                    count=count,
                )
        else:
            seq = await client.fetch_candles(
                symbol=symbol,
                timeframe=target_tf,
                count=count,
            )

        candles_out = [
            {
                "time": int(c.timestamp.timestamp()),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in seq.candles
        ]
        return {
            "symbol": symbol,
            "timeframe": target_tf_label,
            "candles": candles_out,
        }

    async def _store(key: str, payload: dict) -> None:
        try:
            await container.cache.set_with_meta(
                "candles", key, payload, ttl_seconds=TOTAL_TTL_S
            )
        except Exception as e:
            logger.warning(
                "candles_cache_set_failed",
                extra={"key": key, "error": str(e)},
            )

    async def _refresh_under_lock(*, background: bool) -> dict | None:
        """Acquire the single-flight lock and refresh the cache."""
        token = uuid.uuid4().hex
        acquired = await container.cache.try_acquire_lock(
            "candles", lock_key, token, ttl_seconds=LOCK_TTL_S
        )
        if not acquired:
            return None
        try:
            payload = await _fetch_from_broker(
                tf, tf_norm, background=background
            )
            await _store(cache_key, payload)
            return payload
        finally:
            await container.cache.release_lock(
                "candles", lock_key, token
            )

    async def _background_revalidate() -> None:
        """Coordinator-friendly revalidation factory."""
        try:
            await asyncio.wait_for(
                _refresh_under_lock(background=True),
                timeout=BACKGROUND_FETCH_DEADLINE_S,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "candles_background_revalidate_timeout",
                extra={
                    "key": cache_key,
                    "timeout": BACKGROUND_FETCH_DEADLINE_S,
                },
            )
        except Exception as e:
            logger.warning(
                "candles_background_revalidate_failed",
                extra={"key": cache_key, "error": str(e)},
            )

    async def _prewarm_other_timeframes() -> None:
        """Warm every other timeframe for this symbol in the background."""
        for other_tf in _PREWARM_TIMEFRAMES:
            if other_tf == tf_norm:
                continue
            bg_count = 500
            other_key = f"{user.user_id}:{safe_symbol}:{other_tf}:{bg_count}"

            try:
                exists, age = await container.cache.get_meta_only(
                    "candles", other_key
                )
            except Exception:
                exists, age = False, None
            if exists and (age is None or age < REVALIDATE_AFTER_S):
                continue

            token = uuid.uuid4().hex
            lk = f"lock:{other_key}"
            acquired = await container.cache.try_acquire_lock(
                "candles", lk, token, ttl_seconds=LOCK_TTL_S
            )
            if not acquired:
                continue
            try:
                other_tf_enum = _TF_MAP.get(other_tf)
                if other_tf_enum is None:
                    continue
                client = await _resolve_user_broker(
                    container, user.user_id
                )
                with broker_priority(BrokerRequestPriority.BACKGROUND):
                    seq = await asyncio.wait_for(
                        client.fetch_candles(
                            symbol=symbol,
                            timeframe=other_tf_enum,
                            count=bg_count,
                        ),
                        timeout=BACKGROUND_FETCH_DEADLINE_S,
                    )
                payload = {
                    "symbol": symbol,
                    "timeframe": other_tf,
                    "candles": [
                        {
                            "time": int(c.timestamp.timestamp()),
                            "open": c.open,
                            "high": c.high,
                            "low": c.low,
                            "close": c.close,
                            "volume": c.volume,
                        }
                        for c in seq.candles
                    ],
                }
                await _store(other_key, payload)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                msg = str(e).lower()
                rate_limited = (
                    "429" in msg
                    or "too many requests" in msg
                    or "rate limit" in msg
                    or "throttl" in msg
                    or "circuit" in msg
                    or "unavailable" in msg
                    or isinstance(e, asyncio.TimeoutError)
                )
                logger.debug(
                    "candles_prewarm_failed",
                    extra={
                        "symbol": symbol,
                        "timeframe": other_tf,
                        "error": str(e),
                        "aborting_wave": rate_limited,
                    },
                )
                if rate_limited:
                    return
            finally:
                await container.cache.release_lock("candles", lk, token)
            await asyncio.sleep(PREWARM_SPACING_S)

    async def _schedule_revalidate() -> None:
        """Schedule a single-flighted, cooldown-suppressed revalidate."""
        await container.background_tasks.schedule_once(
            revalidate_coord_key,
            _background_revalidate,
            cooldown_s=REVALIDATE_COOLDOWN_S,
            timeout_s=BACKGROUND_FETCH_DEADLINE_S + 5,
        )

    async def _schedule_prewarm() -> None:
        """Schedule a single-flighted, cooldown-suppressed pre-warm wave."""
        await container.background_tasks.schedule_once(
            prewarm_coord_key,
            _prewarm_other_timeframes,
            cooldown_s=PREWARM_COOLDOWN_S,
            timeout_s=PREWARM_WAVE_DEADLINE_S,
        )

    # 1. Fast path: read cache and decide on freshness.
    try:
        cached, age = await container.cache.get_with_meta(
            "candles", cache_key
        )
    except Exception as e:
        logger.warning(
            "candles_cache_get_failed",
            extra={"key": cache_key, "error": str(e)},
        )
        cached, age = None, None

    if cached is not None:
        if age is not None and age >= REVALIDATE_AFTER_S:
            await _schedule_revalidate()
        await _schedule_prewarm()
        return cached

    # 2. Cold-miss path: single-flight under a deadline.
    loop = asyncio.get_event_loop()
    deadline = loop.time() + COLD_FETCH_DEADLINE_S
    try:
        payload = await asyncio.wait_for(
            asyncio.shield(_refresh_under_lock(background=False)),
            timeout=COLD_FETCH_DEADLINE_S,
        )
    except asyncio.TimeoutError:
        payload = None
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "chart_candles_failed",
            extra={
                "symbol": symbol,
                "timeframe": tf_norm,
                "error": str(exc),
                "user_id": user.user_id,
            },
        )
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch candles: {exc}"
        )

    if payload is not None:
        await _schedule_prewarm()
        return payload

    # 3. Wait for another caller's lock to produce the result.
    while loop.time() < deadline:
        await asyncio.sleep(LOCK_WAIT_POLL_S)
        try:
            exists, _ = await container.cache.get_meta_only(
                "candles", cache_key
            )
        except Exception:
            exists = False
        if exists:
            try:
                cached, _ = await container.cache.get_with_meta(
                    "candles", cache_key
                )
            except Exception:
                cached = None
            if cached is not None:
                await _schedule_prewarm()
                return cached

    logger.warning(
        "chart_candles_cold_deadline_exceeded",
        extra={
            "symbol": symbol,
            "timeframe": tf_norm,
            "deadline_seconds": COLD_FETCH_DEADLINE_S,
            "user_id": user.user_id,
        },
    )
    raise HTTPException(
        status_code=504,
        detail=(
            "Chart data is warming up from the broker. "
            "Please retry in a moment."
        ),
    )


@router.websocket("/api/broker/stream-ticks")
async def stream_ticks(websocket: WebSocket):
    """True WebSocket stream of live tick prices for the dashboard chart.

    Protocol (cookie-auth, browser clients):
      1. Browser opens the WS. The gateway-issued access_token cookie
         rides along on the upgrade automatically (HttpOnly, scoped by
         host under RFC 6265 §5.4). The user is resolved from the
         cookie BEFORE the init frame.
      2. Client sends an init frame: { "symbol": "USDJPYm" }.
      3. Server pushes tick frames: { "bid", "ask", "time", "symbol" }.
      4. Client can send a symbol-switch frame at any time:
         { "symbol": "EURUSDm" }.
      5. Either side can close the connection.

    Legacy non-browser clients (CLI tooling):
      The init frame may include a { "token": "<jwt>" } field as a
      last-resort auth channel. This path is preserved for backward
      compatibility only. Browser clients MUST NOT use it because the
      access_token cookie is HttpOnly and cannot be read by JS to copy
      into the init frame.
    """
    from engine.shared.auth import AuthError, verify_token_from_websocket

    await websocket.accept()

    # Step 1: Authenticate from the upgrade cookie / Authorization header.
    # This is the primary path for browser clients. A missing or invalid
    # credential at this stage is NOT immediately fatal: we fall through
    # to the init-frame path so legacy CLI clients that send a token in
    # the first JSON frame still work.
    try:
        user = await verify_token_from_websocket(websocket, init_message=None)
        user_id = user.user_id
    except AuthError:
        user = None
        user_id = ""

    # Step 2: Read the init frame for the symbol (and, for legacy
    # non-browser clients, an optional token field).
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        init_msg = json.loads(raw)
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.close(code=4001, reason="Expected init message with symbol")
        except Exception:
            pass
        return

    symbol = init_msg.get("symbol", "")
    if not symbol:
        try:
            await websocket.close(code=4002, reason="symbol required")
        except Exception:
            pass
        return

    # Step 3: If upgrade-time auth failed, try the init-frame token.
    # This is the legacy path for non-browser CLI clients that hold a
    # token explicitly. Browser clients never reach this branch because
    # their cookie is always present on the upgrade.
    if user is None:
        try:
            user = await verify_token_from_websocket(websocket, init_message=init_msg)
            user_id = user.user_id
        except AuthError as exc:
            try:
                await websocket.close(code=4003, reason=f"Unauthorized: {exc}")
            except Exception:
                pass
            return

    container: Container = websocket.app.state.container
    broker_client = await container.load_user_broker(user_id)
    if broker_client is None:
        try:
            await websocket.close(code=4004, reason="No broker connection configured")
        except Exception:
            pass
        return

    logger.info(
        "tick_stream_connected",
        extra={"user_id": user_id, "symbol": symbol},
    )

    # Step 3: Stream ticks in a loop.
    try:
        while True:
            # Check for incoming messages (symbol switch or close).
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                msg = json.loads(raw)
                new_symbol = msg.get("symbol", "")
                if new_symbol:
                    symbol = new_symbol
                    logger.debug(
                        "tick_stream_symbol_switch",
                        extra={"user_id": user_id, "new_symbol": symbol},
                    )
            except asyncio.TimeoutError:
                pass  # No incoming message — continue streaming.

            # Fetch the latest tick from the broker.
            try:
                tick = await broker_client.get_tick_price(symbol)
                await websocket.send_json({
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "time": tick.time,
                    "symbol": symbol,
                })
            except Exception as exc:
                # Send error frame but don't disconnect — transient broker glitch.
                await websocket.send_json({
                    "error": str(exc),
                    "symbol": symbol,
                })
                await asyncio.sleep(2.0)  # Back off on error.

    except WebSocketDisconnect:
        logger.info(
            "tick_stream_disconnected",
            extra={"user_id": user_id, "symbol": symbol},
        )
    except Exception as exc:
        logger.error(
            "tick_stream_error",
            extra={"user_id": user_id, "symbol": symbol, "error": str(exc)},
        )
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass


@router.websocket("/api/broker/stream-positions")
async def stream_positions(websocket: WebSocket):
    """WebSocket stream of live position updates.

    Protocol (cookie-auth):
      1. Browser opens the WS — access_token cookie rides along
         automatically; the user is resolved from the cookie BEFORE
         any init frame. An optional init frame `{}` (or `{ token }`
         for legacy CLI clients) is accepted but not required.
      2. Server polls positions every 1 s and pushes diffs:
         [{ "ticket": 12345, "sl": 1.05, "tp": 1.10, ... }]
    """
    from engine.shared.auth import AuthError, verify_token_from_websocket

    await websocket.accept()

    # Step 1: Authenticate from the upgrade cookie / header first.
    try:
        user = await verify_token_from_websocket(websocket, init_message=None)
        user_id = user.user_id
    except AuthError:
        user = None
        user_id = ""

    # Step 2: For legacy clients, accept an init frame carrying a
    # `token` field. Cookie-auth browsers don't need an init frame at
    # all; we tolerate a missing one in that case.
    if user is None:
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            init_msg = json.loads(raw)
        except WebSocketDisconnect:
            return
        except Exception:
            try:
                await websocket.close(code=4001, reason="Expected init message with token")
            except Exception:
                pass
            return

        try:
            user = await verify_token_from_websocket(websocket, init_message=init_msg)
            user_id = user.user_id
        except AuthError as exc:
            try:
                await websocket.close(code=4003, reason=f"Unauthorized: {exc}")
            except Exception:
                pass
            return

    container: Container = websocket.app.state.container
    broker_client = await container.load_user_broker(user_id)
    if broker_client is None:
        try:
            await websocket.close(code=4004, reason="No broker connection configured")
        except Exception:
            pass
        return

    logger.info("position_stream_connected", extra={"user_id": user_id})

    # Cache last state to only push on diffs
    last_state_hash = ""

    try:
        while True:
            # Check for client disconnect
            try:
                _ = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass  # normal timeout, continue polling
            except WebSocketDisconnect:
                break

            try:
                positions = await asyncio.wait_for(broker_client.get_positions(), timeout=2.0)

                # Serialize
                result = [
                    {
                        "symbol": p.symbol,
                        "type": 0 if p.direction == "BUY" else 1,
                        "price_open": p.entry_price,
                        "price_current": p.current_price,
                        "sl": p.stop_loss,
                        "tp": p.take_profit,
                        "volume": p.volume,
                        "profit": p.profit,
                        "ticket": int(p.ticket) if p.ticket.isdigit() else 0,
                    }
                    for p in positions
                ]

                # Check for diff
                current_hash = hashlib.md5(json.dumps(result, sort_keys=True).encode()).hexdigest()
                if current_hash != last_state_hash:
                    await websocket.send_json(result)
                    last_state_hash = current_hash

            except Exception as exc:
                logger.warning("position_stream_poll_error", extra={"error": str(exc), "user_id": user_id})
                await asyncio.sleep(2.0)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("position_stream_error", extra={"error": str(exc), "user_id": user_id})
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass
    finally:
        logger.info("position_stream_disconnected", extra={"user_id": user_id})

