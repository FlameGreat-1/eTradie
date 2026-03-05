"""Structured JSON logger factory.

Uses ``structlog`` to produce JSON-formatted log lines that include
correlation IDs, timestamps in ISO-8601, and log level as a top-level field.
Every log entry is machine-parseable for ingestion into ELK / Loki / etc.
"""

from __future__ import annotations

import logging
import sys
from typing import Any
from uuid import uuid4

import structlog
from structlog.types import Processor

_CONFIGURED = False


def _add_log_level_upper(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Normalise the log level to uppercase for consistency."""
    if "level" in event_dict:
        event_dict["level"] = event_dict["level"].upper()
    return event_dict


def _drop_color_message(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Remove uvicorn's color_message key that pollutes JSON output."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(*, log_level: str = "INFO", json_output: bool = True) -> None:
    """Initialise structured logging for the entire application.

    Must be called exactly once during application startup.  Subsequent
    calls are silently ignored to prevent double-configuration.

    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: If ``True``, emit JSON lines.  If ``False``, use
            coloured console output (useful for local development).
    """
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    _CONFIGURED = True

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_log_level_upper,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _drop_color_message,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())

    # Quieten noisy third-party loggers
    for noisy in ("aiohttp", "asyncio", "urllib3", "sqlalchemy.engine", "httpcore", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger for the given module name."""
    return structlog.get_logger(name)


def bind_correlation_id(correlation_id: str | None = None) -> str:
    """Bind a correlation ID to the current context for request tracing.

    Returns the correlation ID (generated if not provided).
    """
    cid = correlation_id or uuid4().hex
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    return cid


def clear_contextvars() -> None:
    """Clear all bound context variables (call at end of request/cycle)."""
    structlog.contextvars.clear_contextvars()
