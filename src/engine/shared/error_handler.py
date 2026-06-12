"""Global last-resort exception handler for the FastAPI engine.

FastAPI already installs handlers for ``HTTPException`` and
``RequestValidationError``, and every router maps the typed
``ETradieBaseError`` subclasses to precise status codes (with
``Retry-After`` where relevant) inside its own handlers. None of that
is affected here.

What is NOT covered by any of the above is a genuinely *unhandled*
exception escaping a route or middleware: by default Starlette logs a
bare traceback and returns ``Internal Server Error`` as plain text.
This module installs a single catch-all handler that instead:

  * logs the failure with full structured post-mortem context through
    the shared ``log_panic_recovery`` helper (secret-sanitized,
    ``trace_id`` / ``correlation_id`` auto-bound from contextvars), and
  * returns a sanitized generic JSON 500, so no internal error string,
    exception type, or stack trace is ever returned to the caller.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from engine.shared.logging import get_logger, log_panic_recovery

logger = get_logger(__name__)

_GENERIC_500_BODY = {"detail": "internal server error"}


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log the unhandled exception and return a sanitized 500."""
    log_panic_recovery(
        logger,
        exc,
        operation=f"{request.method} {request.url.path}",
    )
    return JSONResponse(status_code=500, content=_GENERIC_500_BODY)


def register_exception_handlers(app: FastAPI) -> None:
    """Install the catch-all exception handler on the FastAPI app.

    Registered for the base ``Exception`` type so it fires only for
    exceptions not already claimed by a more specific handler
    (``HTTPException``, ``RequestValidationError``) or by a router's
    own try/except mapping.
    """
    app.add_exception_handler(Exception, _unhandled_exception_handler)
