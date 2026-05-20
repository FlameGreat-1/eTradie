"""Internal broker bridge endpoints (Go Execution + Management).

These endpoints proxy broker operations from the Go services through
the Python engine's active broker client (MetaApiClient or ZmqClient).
The Go services call these at EXECUTION_BROKER_BRIDGE_URL and
MANAGEMENT_BROKER_BRIDGE_URL (both http://engine:8000).

Routes:
    GET  /internal/broker/account_info
    GET  /internal/broker/positions
    GET  /internal/broker/history
    GET  /internal/broker/pending_orders
    GET  /internal/broker/symbol_info
    GET  /internal/broker/tick_price
    POST /internal/broker/place_order
    POST /internal/broker/cancel_order
    GET  /internal/broker/position
    POST /internal/broker/modify_position
    POST /internal/broker/close_partial
    POST /internal/broker/close_position
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from engine.dependencies import Container
from engine.helpers import _resolve_user_broker
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.internal_auth import verify_internal_auth
from engine.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/internal/broker/account_info")
async def broker_account_info(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Return live account balance, equity, margin, free margin.
    Uses a Stale-While-Revalidate pattern with Redis to survive ZMQ lockouts.
    """
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    cache_key = f"cache_failover:account_info:{user_id}"

    try:
        # Enforce a strict 2-second timeout. If the ZMQ lock is held by a massive
        # background candle fetch, this will timeout and drop to the Redis cache failover.
        info = await asyncio.wait_for(broker_client.get_account_info(), timeout=2.0)
        result = {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "margin_free": info.free_margin,
            "currency": info.currency,
        }
        # Update the failover cache silently
        try:
            await container.cache.set("internal", cache_key, result, ttl_seconds=86400)
        except Exception:
            pass
        return result
    except (asyncio.TimeoutError, Exception) as exc:
        # Failover to the last known state in Redis instead of throwing a 503
        try:
            cached = await container.cache.get("internal", cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        logger.error("broker_account_info_failed_no_cache", extra={"error": str(exc), "user_id": user_id})
        # Return empty skeleton to prevent 502s from bubbling up to the dashboard UI
        return {"balance": 0, "equity": 0, "margin": 0, "margin_free": 0, "currency": "USD"}


@router.get("/internal/broker/positions")
async def broker_positions(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> list:
    """Return all open positions at the broker.
    Uses a Stale-While-Revalidate pattern with Redis to survive ZMQ lockouts.
    """
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    cache_key = f"cache_failover:positions:{user_id}"

    try:
        positions = await asyncio.wait_for(broker_client.get_positions(), timeout=2.0)
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
                "comment": p.comment,
                "time_setup": p.open_time,
            }
            for p in positions
        ]
        # Update the failover cache silently.
        # TTL is intentionally short (15 s) because positions are highly
        # dynamic.  A long TTL (the previous 24 h) caused stale empty
        # snapshots to persist through ZMQ contention windows, making
        # manually-placed MT5 trades invisible to the dashboard.
        try:
            await container.cache.set("internal", cache_key, result, ttl_seconds=15)
        except Exception:
            pass
        return result
    except (asyncio.TimeoutError, Exception) as exc:
        # Failover to the last known state in Redis instead of throwing a 503
        try:
            cached = await container.cache.get("internal", cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        logger.error("broker_positions_failed_no_cache", extra={"error": str(exc), "user_id": user_id})
        # Return empty list to prevent 502s from bubbling up to the dashboard UI
        return []


@router.get("/internal/broker/history")
async def broker_history(
    request: Request,
    days: int = 30,
    _: None = Depends(verify_internal_auth),
) -> list:
    """Return historical closed deals at the broker."""
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    cache_key = f"cache_failover:history:{user_id}:{days}"

    try:
        history = await asyncio.wait_for(broker_client.get_history(days=days), timeout=5.0)
        result = [
            {
                "ticket": h.ticket,
                "position_id": h.position_id,
                "symbol": h.symbol,
                "direction": h.direction,
                "volume": h.volume,
                "price": h.price,
                "profit": h.profit,
                "commission": h.commission,
                "swap": h.swap,
                "time": h.time,
                "comment": h.comment,
            }
            for h in history
        ]
        try:
            await container.cache.set("internal", cache_key, result, ttl_seconds=86400)
        except Exception:
            pass
        return result
    except (asyncio.TimeoutError, Exception) as exc:
        try:
            cached = await container.cache.get("internal", cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass
        return []


@router.get("/internal/broker/pending_orders")
async def broker_pending_orders(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> list:
    """Return all pending limit/stop orders at the broker."""
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    cache_key = f"cache_failover:pending_orders:{user_id}"

    try:
        orders = await asyncio.wait_for(broker_client.get_pending_orders(), timeout=2.0)
        result = [
            {
                "symbol": o.symbol,
                "type": o.order_type,
                "price_open": o.price,
                "sl": o.stop_loss,
                "tp": o.take_profit,
                "volume": o.volume,
                "ticket": int(o.ticket) if o.ticket.isdigit() else 0,
                "comment": o.comment,
                "time_setup": o.open_time,
            }
            for o in orders
        ]

        # Short TTL — pending orders change frequently.
        try:
            await container.cache.set("internal", cache_key, result, ttl_seconds=15)
        except Exception:
            pass
        return result
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("zmq_execution_lock_timeout_falling_back_to_pending_orders_cache", extra={"error": str(exc), "user_id": user_id})

        try:
            cached_orders = await container.cache.get("internal", cache_key)
            if cached_orders is not None:
                return cached_orders
        except Exception:
            pass

        return []


@router.get("/internal/broker/symbol_info")
async def broker_symbol_info(
    request: Request,
    symbol: str = "",
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Return instrument metadata for the Go sizing engine.
    Uses a Stale-While-Revalidate pattern with Redis to survive ZMQ lockouts.
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol parameter required")
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    cache_key = f"cache_failover:symbol_info:{user_id}:{symbol}"

    try:
        # Enforce a strict 2-second timeout to prevent Go client timeout race.
        info = await asyncio.wait_for(broker_client.get_symbol_info(symbol), timeout=2.0)
        # Update the failover cache silently
        try:
            await container.cache.set("internal", cache_key, info, ttl_seconds=86400 * 7)
        except Exception:
            pass
        return info
    except (asyncio.TimeoutError, Exception) as exc:
        # Failover to the last known state in Redis instead of throwing a 502
        try:
            cached = await container.cache.get("internal", cache_key)
            if cached:
                return cached
        except Exception:
            pass

        logger.error(
            "broker_symbol_info_failed_no_cache", extra={"symbol": symbol, "error": str(exc), "user_id": user_id}
        )
        raise HTTPException(
            status_code=502, detail=f"Symbol info unavailable and no cache: {exc}"
        )


@router.get("/internal/broker/tick_price")
async def broker_tick_price(
    request: Request,
    symbol: str = "",
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Return latest bid/ask for a symbol.

    Called by both Execution (watcher tick polling) and Management
    (per-trade monitoring worker) on every tick cycle.
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol parameter required")
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    try:
        tick = await broker_client.get_tick_price(symbol)
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "time": tick.time,
        }
    except Exception as exc:
        logger.error(
            "broker_tick_price_failed", extra={"symbol": symbol, "error": str(exc), "user_id": user_id}
        )
        raise HTTPException(
            status_code=502, detail=f"Tick price unavailable: {exc}"
        )


@router.post("/internal/broker/place_order")
async def broker_place_order(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Place a limit or market order at the broker.

    Called by Execution Module B's bridge.go placeOrder().
    The Go gateway sends X-User-Id so the engine resolves the correct
    per-user broker connection.
    """
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    body = await request.json()

    symbol = body.get("symbol", "")
    direction = body.get("direction", "")
    order_type = body.get("order_type", "MARKET")
    price = float(body.get("price", 0))
    stop_loss = float(body.get("stop_loss", 0))
    take_profit = float(body.get("take_profit", 0))
    lot_size = float(body.get("lot_size", 0))
    comment = body.get("comment", "")

    if not symbol or not direction:
        raise HTTPException(status_code=400, detail="symbol and direction required")

    try:
        result = await broker_client.place_order(
            symbol=symbol,
            direction=direction,
            order_type=order_type,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lot_size=lot_size,
            comment=comment,
        )
        return {
            "order_id": result.order_id,
            "price": result.price,
            "status": result.status,
            "error": result.error,
        }
    except Exception as exc:
        logger.error(
            "broker_place_order_failed",
            extra={"symbol": symbol, "direction": direction, "error": str(exc), "user_id": user_id},
        )
        raise HTTPException(
            status_code=502, detail=f"Order placement failed: {exc}"
        )


@router.post("/internal/broker/cancel_order")
async def broker_cancel_order(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Cancel a pending order by broker order ID."""
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    body = await request.json()
    order_id = str(body.get("order_id", ""))

    if not order_id:
        raise HTTPException(status_code=400, detail="order_id required")

    try:
        success = await broker_client.cancel_order(order_id)
        return {"success": success, "error": ""}
    except Exception as exc:
        logger.error(
            "broker_cancel_order_failed",
            extra={"order_id": order_id, "error": str(exc), "user_id": user_id},
        )
        return {"success": False, "error": str(exc)}


@router.get("/internal/broker/position")
async def broker_position(
    request: Request,
    ticket: str = "",
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Return a single open position by broker ticket.

    Called by Management Module C's stream.go GetPosition().
    """
    if not ticket:
        raise HTTPException(status_code=400, detail="ticket parameter required")
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    try:
        p = await broker_client.get_position(ticket)
        return {
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
    except Exception as exc:
        logger.error(
            "broker_position_failed", extra={"ticket": ticket, "error": str(exc), "user_id": user_id}
        )
        raise HTTPException(status_code=502, detail=f"Position unavailable: {exc}")


@router.post("/internal/broker/modify_position")
async def broker_modify_position(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Modify SL/TP on an existing open position.

    Called by Management Module C's client.go ModifyPosition().
    """
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    body = await request.json()

    ticket = str(body.get("ticket", ""))
    stop_loss = float(body.get("stop_loss", 0))
    take_profit = float(body.get("take_profit", 0))

    if not ticket:
        raise HTTPException(status_code=400, detail="ticket required")

    try:
        success = await broker_client.modify_position(
            ticket=ticket,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        return {"success": success, "error": ""}
    except Exception as exc:
        logger.error(
            "broker_modify_position_failed",
            extra={"ticket": ticket, "error": str(exc), "user_id": user_id},
        )
        return {"success": False, "error": str(exc)}


@router.post("/internal/broker/close_partial")
async def broker_close_partial(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Partially close a position by volume.

    Called by Management Module C's client.go ClosePartial().
    """
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    body = await request.json()

    ticket = str(body.get("ticket", ""))
    volume = float(body.get("volume", 0))

    if not ticket or volume <= 0:
        raise HTTPException(
            status_code=400, detail="ticket and positive volume required"
        )

    try:
        result = await broker_client.close_partial(
            ticket=ticket,
            volume=volume,
        )
        return {
            "success": result.get("success", False),
            "close_price": result.get("close_price", 0),
            "error": result.get("error", ""),
        }
    except Exception as exc:
        logger.error(
            "broker_close_partial_failed",
            extra={"ticket": ticket, "volume": volume, "error": str(exc), "user_id": user_id},
        )
        return {"success": False, "close_price": 0, "error": str(exc)}


@router.post("/internal/broker/close_position")
async def broker_close_position(
    request: Request,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Fully close a position at market.

    Called by Management Module C's client.go ClosePosition().
    """
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    broker_client = await _resolve_user_broker(container, user_id)
    body = await request.json()

    ticket = str(body.get("ticket", ""))

    if not ticket:
        raise HTTPException(status_code=400, detail="ticket required")

    try:
        result = await broker_client.close_position(ticket)
        return {
            "success": result.get("success", False),
            "close_price": result.get("close_price", 0),
            "error": result.get("error", ""),
        }
    except Exception as exc:
        logger.error(
            "broker_close_position_failed",
            extra={"ticket": ticket, "error": str(exc), "user_id": user_id},
        )
        return {"success": False, "close_price": 0, "error": str(exc)}
