"""Request body-size limiting for the Python FastAPI engine.

TIER 4 API Security — "Length limits". FastAPI/uvicorn impose no cap on
the size of a request body by default. Several /internal/broker/*
endpoints on the order path decode the body with a raw
``await request.json()`` and a few user-facing routes accept Pydantic
models; in BOTH cases an arbitrarily large body would be buffered into
memory before any handler logic runs. This middleware is the single
authoritative request-body size limit for the engine, mirroring the
Go services' auth.MaxJSONBodyBytes / http.MaxBytesReader cap.

It is a pure ASGI middleware (not BaseHTTPMiddleware) so it can both:
  * short-circuit on the declared Content-Length BEFORE the body is
    read, and
  * wrap the ASGI ``receive`` to count bytes for chunked / unknown-
    length bodies, aborting with 413 the moment the running total
    exceeds the cap — so a streaming body can never be buffered past
    the limit downstream.

GET/HEAD/OPTIONS/DELETE-with-no-body requests carry no body and are
unaffected. The SSE streaming RESPONSE is outbound and is likewise
unaffected (this middleware only bounds the inbound request body).
"""
from __future__ import annotations

import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Default 8 MiB. Sized for the platform's genuinely HEAVY internal
# payloads so a legitimate analysis cycle is never 413'd:
#
#   * /internal/processor/process carries processor_input = the full
#     13-timeframe TA snapshots + all SMC/SnD candidates + 8 macro
#     datasets + the full RAG bundle + metadata. processor/config.py
#     documents the rendered LLM user message as "~280KB ... 26 RAG
#     chunks"; the raw assembled input the gateway POSTs is the source
#     material for that prompt and can be in the same order of
#     magnitude or larger.
#   * /internal/debug/runcycle is the LARGEST body on the platform: it
#     bundles ta_data + macro_data + rag_data + processor_data +
#     execution_request in one payload.
#
# 8 MiB is ~28x the documented ~280KB prompt and comfortably above any
# realistic combined assembled payload, yet still far below anything
# that could threaten an engine pod's memory under a flood. The small,
# flat dashboard + connection-CRUD bodies sit at a few KB and are
# unaffected. Overridable via ENGINE_MAX_REQUEST_BODY_BYTES so an
# operator can tighten or (rarely) loosen it without a code change.
_DEFAULT_MAX_BODY_BYTES = 8 * 1024 * 1024


def _load_max_body_bytes() -> int:
    raw = os.environ.get("ENGINE_MAX_REQUEST_BODY_BYTES", "").strip()
    if not raw:
        return _DEFAULT_MAX_BODY_BYTES
    try:
        val = int(raw)
    except ValueError:
        return _DEFAULT_MAX_BODY_BYTES
    if val <= 0:
        return _DEFAULT_MAX_BODY_BYTES
    return val


async def _send_413(send: Send) -> None:
    """Emit a minimal JSON 413 response."""
    body = b'{"detail":"request body too large"}'
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class MaxBodySizeMiddleware:
    """Pure ASGI middleware that bounds the inbound request body size.

    Construction reads ENGINE_MAX_REQUEST_BODY_BYTES once at startup so
    the limit is fixed for the process lifetime (consistent with how
    CSRFMiddleware reads its config at construction).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.max_bytes = _load_max_body_bytes()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Fast path: reject on a declared, over-limit Content-Length
        # before reading a single body byte.
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value.decode().strip())
                except ValueError:
                    declared = -1
                if declared > self.max_bytes:
                    await _send_413(send)
                    return
                break

        # Slow path: count bytes as the body streams in. This covers
        # chunked transfer-encoding and any client that omits or lies
        # about Content-Length.
        #
        # Enforcement contract (both halves matter):
        #   * MEMORY: the moment the running total exceeds the cap,
        #     limited_receive STOPS delivering real body bytes to the
        #     app. It returns a terminal empty http.request
        #     (more_body=False) so the handler's body read ends
        #     immediately, then http.disconnect for any further pulls.
        #     The over-limit bytes are never handed to the handler, so
        #     nothing downstream can buffer them.
        #   * RESPONSE: guarded_send maps the over-limit condition to a
        #     single clean 413 IFF the app has not already committed a
        #     response. FastAPI reads the body (json()/Pydantic) before
        #     returning, so the limit always trips before any
        #     http.response.start; the "already committed" branch is a
        #     defensive fallthrough that forwards the app's own response
        #     unchanged rather than corrupting the ASGI stream with a
        #     second response.start.
        received = 0
        limit = self.max_bytes
        too_large = False
        terminated = False  # emitted the terminal empty body to the app

        async def limited_receive() -> Message:
            nonlocal received, too_large, terminated
            # Once over the cap, never pull more real body from the
            # client into the app: first hand back a terminal empty
            # chunk, then disconnect.
            if too_large:
                if not terminated:
                    terminated = True
                    return {"type": "http.request", "body": b"", "more_body": False}
                return {"type": "http.disconnect"}

            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Trip the flag and DO NOT forward the over-limit
                    # bytes to the app: substitute a terminal empty
                    # chunk so the handler's body read stops here.
                    too_large = True
                    terminated = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        response_started = False

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if too_large and not response_started:
                response_started = True
                await _send_413(send)
                return
            if too_large:
                # App already committed a response before we tripped
                # (does not occur on FastAPI's read-then-return path).
                # Forward unchanged rather than emitting a second,
                # conflicting response.start.
                await send(message)
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        await self.app(scope, limited_receive, guarded_send)
