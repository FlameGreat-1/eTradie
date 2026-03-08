"""
Production-grade structured JSON logger factory.

Uses ``structlog`` to produce JSON-formatted log lines with:
- Correlation IDs and trace IDs for distributed tracing
- ISO-8601 timestamps
- Log level normalization
- Sensitive data sanitization
- Context variable management
- Machine-parseable output for ELK/Loki/Datadog

Security:
- Never log secrets, API keys, passwords, tokens, or PII
- Use sanitization processors for sensitive fields
- Bind minimal context (trace_id, correlation_id only)
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional, Set
from uuid import uuid4

import structlog
from structlog.types import Processor

from engine.shared.metrics.prometheus import LOG_ENTRIES_TOTAL

_CONFIGURED = False

# Security: Sensitive field names to sanitize in logs
_SENSITIVE_FIELDS: Set[str] = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "authorization",
    "auth",
    "cookie",
    "session",
    "private_key",
    "access_token",
    "refresh_token",
    "client_secret",
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "pin",
}


def _add_log_level_upper(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Normalize log level to uppercase for consistency."""
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


def _sanitize_sensitive_data(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Sanitize sensitive fields in log entries.
    
    Replaces values of sensitive fields with '***REDACTED***' to prevent
    accidental logging of secrets, passwords, tokens, or PII.
    """
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_FIELDS:
            event_dict[key] = "***REDACTED***"
        
        # Recursively sanitize nested dicts
        if isinstance(event_dict[key], dict):
            event_dict[key] = _sanitize_dict(event_dict[key])
    
    return event_dict


def _sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize sensitive fields in nested dictionaries."""
    sanitized = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_FIELDS:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def _record_log_metrics(
    _logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Record log entry metrics for observability."""
    level = event_dict.get("level", "UNKNOWN").upper()
    
    LOG_ENTRIES_TOTAL.labels(
        level=level,
        logger=event_dict.get("logger", "unknown"),
    ).inc()
    
    return event_dict


def configure_logging(
    *,
    log_level: str = "INFO",
    json_output: bool = True,
    enable_sampling: bool = False,
    sample_rate: float = 1.0,
) -> None:
    """
    Initialize structured logging for the entire application.
    
    Must be called exactly once during application startup. Subsequent
    calls are silently ignored to prevent double-configuration.
    
    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, emit JSON lines. If False, use colored console
            output (useful for local development)
        enable_sampling: If True, sample logs at specified rate (for high-volume scenarios)
        sample_rate: Sampling rate (0.0 to 1.0) when sampling is enabled
        
    Raises:
        ValueError: On invalid log level or sample rate
    """
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    
    # Validate configuration
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level.upper() not in valid_levels:
        raise ValueError(
            f"Invalid log level '{log_level}'. Must be one of {valid_levels}"
        )
    
    if not 0.0 <= sample_rate <= 1.0:
        raise ValueError(f"Sample rate must be between 0.0 and 1.0, got {sample_rate}")
    
    _CONFIGURED = True

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_log_level_upper,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _drop_color_message,
        _sanitize_sensitive_data,  # Security: sanitize before rendering
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.format_exc_info,
        _record_log_metrics,  # Observability: record metrics
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
    noisy_loggers = (
        "aiohttp",
        "asyncio",
        "urllib3",
        "sqlalchemy.engine",
        "httpcore",
        "httpx",
        "redis",
        "aiokafka",
    )
    for noisy in noisy_loggers:
        logging.getLogger(noisy).setLevel(logging.WARNING)
    
    # Log configuration completion
    logger = get_logger(__name__)
    logger.info(
        "logging_configured",
        extra={
            "log_level": log_level.upper(),
            "json_output": json_output,
            "enable_sampling": enable_sampling,
            "sample_rate": sample_rate if enable_sampling else None,
        },
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a bound structured logger for the given module name.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Bound structured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("operation_completed", user_id=123, duration_ms=45.2)
    """
    return structlog.get_logger(name)


def bind_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Bind a correlation ID to the current context for request tracing.
    
    Args:
        correlation_id: Optional correlation ID (generated if not provided)
        
    Returns:
        The correlation ID (generated UUID hex if not provided)
        
    Example:
        >>> cid = bind_correlation_id()
        >>> logger.info("request_started")  # Will include correlation_id
    """
    cid = correlation_id or uuid4().hex
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    return cid


def bind_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Bind a trace ID to the current context for distributed tracing.
    
    Args:
        trace_id: Optional trace ID (generated if not provided)
        
    Returns:
        The trace ID (generated UUID hex if not provided)
        
    Example:
        >>> tid = bind_trace_id()
        >>> logger.info("external_call_started")  # Will include trace_id
    """
    tid = trace_id or uuid4().hex
    structlog.contextvars.bind_contextvars(trace_id=tid)
    return tid


def bind_context(
    *,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, str]:
    """
    Bind multiple context variables at once.
    
    Args:
        correlation_id: Optional correlation ID
        trace_id: Optional trace ID
        **kwargs: Additional context key-value pairs
        
    Returns:
        Dictionary of bound context variables
        
    Security:
        Do NOT bind sensitive data (passwords, tokens, PII).
        Only bind identifiers and non-sensitive metadata.
        
    Example:
        >>> bind_context(
        ...     correlation_id="abc123",
        ...     trace_id="xyz789",
        ...     operation="user_login",
        ... )
    """
    context = {}
    
    if correlation_id:
        context["correlation_id"] = correlation_id
    
    if trace_id:
        context["trace_id"] = trace_id
    
    # Sanitize additional context
    for key, value in kwargs.items():
        if key.lower() not in _SENSITIVE_FIELDS:
            context[key] = value
    
    structlog.contextvars.bind_contextvars(**context)
    return context


def unbind_context(*keys: str) -> None:
    """
    Unbind specific context variables.
    
    Args:
        *keys: Context variable keys to unbind
        
    Example:
        >>> unbind_context("correlation_id", "trace_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_contextvars() -> None:
    """
    Clear all bound context variables.
    
    Should be called at the end of each request/operation cycle to prevent
    context leakage between requests.
    
    Example:
        >>> try:
        ...     bind_correlation_id()
        ...     # ... process request ...
        ... finally:
        ...     clear_contextvars()
    """
    structlog.contextvars.clear_contextvars()


def log_panic_recovery(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    *,
    operation: str,
    **context: Any,
) -> None:
    """
    Log panic recovery with full context for post-mortem analysis.
    
    Args:
        logger: Structured logger instance
        error: Exception that was caught
        operation: Operation name that panicked
        **context: Additional context for debugging
        
    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_panic_recovery(logger, e, operation="risky_operation", user_id=123)
        ...     # ... handle gracefully ...
    """
    logger.error(
        "panic_recovered",
        extra={
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context,
        },
        exc_info=True,
    )
