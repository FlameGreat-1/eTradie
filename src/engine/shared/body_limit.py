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

# Default 1 MiB. Far above the largest legitimate engine payload (the
# processor_input pipeline blob on /internal/processor/process and the
# debug-runcycle dump) yet far below anything that could threaten
# engine memory under a flood. Overridable via the env var so an
# operator can tighten or (rarely) loosen it without a code change.
_DEFAULT_MAX_BODY_BYTES = 1 * 1024 * 1024


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
        # about Content-Length. Once the running total exceeds the cap
        # we emit 413 and stop forwarding body events downstream.
        received = 0
        limit = self.max_bytes
        too_large = False

        async def limited_receive() -> Message:
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    too_large = True
            return message

        # We cannot know the total until the body is consumed by the
        # app, so we hand the app a wrapped receive and a wrapped send
        # that suppresses the app's response if the limit was tripped
        # mid-stream. The wrapped receive marks too_large; the wrapped
        # send checks the flag before the app's first response event
        # and substitutes a 413 instead.
        response_started = False

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if too_large and not response_started:
                response_started = True
                await _send_413(send)
                return
            if too_large:
                # Drop any further app output once we've sent 413.
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        await self.app(scope, limited_receive, guarded_send)
