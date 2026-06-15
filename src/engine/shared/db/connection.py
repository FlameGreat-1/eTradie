from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import event, text
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    OperationalError,
)
from sqlalchemy.exc import (
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import QueuePool

from engine.shared.exceptions import (
    DatabaseConnectionError,
    DatabaseIntegrityError,
    DatabaseOperationalError,
    DatabaseTimeoutError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    DB_CONNECTION_POOL_SIZE,
    DB_OPERATION_DURATION,
    DB_OPERATION_ERRORS,
)

logger = get_logger(__name__)


# libpq's `sslmode` query-string value mapped to asyncpg's `ssl=` kwarg.
#
# Why this exists at all:
#   asyncpg has its own native Postgres protocol implementation, separate
#   from libpq. It does NOT accept the libpq-style `sslmode` kwarg —
#   asyncpg.connect() raises:
#     TypeError: connect() got an unexpected keyword argument 'sslmode'
#   So we must strip `sslmode` from the URL we hand to SQLAlchemy +
#   asyncpg, and substitute the corresponding asyncpg `ssl` kwarg via
#   create_async_engine's connect_args.
#
# What `ssl=` value to use depends on the deployment topology, NOT on
# the libpq sslmode value alone. Two modes are supported:
#
#   MESH mode (ENGINE_DB_NATIVE_TLS=false, the DEFAULT):
#     The cluster's Linkerd service mesh encrypts the wire between the
#     engine pod and the postgres pod. The postgres SERVER on :5432 is
#     plaintext (see helm/data-layer/templates/postgres-statefulset.yaml —
#     no TLS args, no cert mount). The chart-rendered postgres-exporter
#     sidecar connects with sslmode=disable (same architectural reason).
#     asyncpg-level TLS would attempt a server-side SSL upgrade which
#     postgres rejects (ConnectionError: rejected SSL upgrade). In MESH
#     mode we therefore pass ssl=False regardless of the URL's sslmode
#     value — Linkerd is doing the encryption, asyncpg should not try.
#
#   NATIVE mode (ENGINE_DB_NATIVE_TLS=true, opt-in):
#     Used when postgres serves real TLS (e.g. managed databases like
#     Neon / RDS / Aurora / Cloud SQL). The libpq sslmode -> asyncpg ssl
#     mapping is the documented one:
#       sslmode=disable      -> ssl=False
#       sslmode=require      -> ssl='require'
#       sslmode=verify-ca    -> ssl='verify-ca'
#       sslmode=verify-full  -> ssl='verify-full'
#
# In BOTH modes the validator in engine.config
# (Settings._validate_production_secrets) still inspects the ORIGINAL
# URL string and rejects URLs without sslmode in {require, verify-ca,
# verify-full}. That is a string-level Tier 11 audit-trail invariant
# (config intends TLS); the wire-level translation here is a separate
# concern.
_LIBPQ_SSLMODE_TO_ASYNCPG_SSL_NATIVE: dict[str, Any] = {
    "disable": False,
    "require": "require",
    "verify-ca": "verify-ca",
    "verify-full": "verify-full",
}


def _engine_db_native_tls() -> bool:
    """Read ENGINE_DB_NATIVE_TLS env var. Default false (Linkerd-mesh
    topology, postgres plaintext on the wire). Set true for managed-
    postgres deployments where the server actually serves TLS.
    """
    return os.environ.get("ENGINE_DB_NATIVE_TLS", "false").strip().lower() in {"1", "true", "yes", "on"}


def _translate_sslmode_for_asyncpg(url: str) -> tuple[str, Any]:
    """Strip the libpq `sslmode` query param from a Postgres URL and
    return the cleaned URL plus the asyncpg `ssl` kwarg value.

    The `ssl` kwarg value depends on ENGINE_DB_NATIVE_TLS:
      * false (default, MESH mode): ssl=False regardless of sslmode.
        Linkerd handles encryption.
      * true (NATIVE mode): use the libpq-to-asyncpg mapping above.

    All OTHER query params are preserved verbatim.

    Returns (cleaned_url, ssl_kwarg_value_or_None).
      * If the URL has no `sslmode`, returns (url, None) and caller
        passes connect_args unchanged.
      * If `sslmode` is present, returns (cleaned_url, computed_value).
    """
    parsed = urlparse(url)
    if not parsed.query:
        return url, None

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    kept_pairs: list[tuple[str, str]] = []
    sslmode_value: str | None = None
    for key, value in pairs:
        if key.lower() == "sslmode":
            sslmode_value = value
            continue
        kept_pairs.append((key, value))

    if sslmode_value is None:
        return url, None

    cleaned_url = urlunparse(parsed._replace(query=urlencode(kept_pairs, doseq=True)))

    if not _engine_db_native_tls():
        # MESH mode: Linkerd encrypts the wire; asyncpg must not attempt
        # a server-side TLS upgrade that postgres-in-cluster would reject.
        return cleaned_url, False

    # NATIVE mode: libpq-to-asyncpg ssl mapping.
    ssl_kwarg = _LIBPQ_SSLMODE_TO_ASYNCPG_SSL_NATIVE.get(sslmode_value.strip().lower())
    if ssl_kwarg is None and sslmode_value.strip().lower() not in {"allow", "prefer"}:
        logger.warning(
            "unknown_sslmode_value",
            extra={"sslmode": sslmode_value, "action": "falling_back_to_asyncpg_default"},
        )
    return cleaned_url, ssl_kwarg


class DatabaseManager:
    """
    Production-grade async database connection manager.

    Provides:
    - Connection pooling with health monitoring
    - Automatic transaction management
    - Query timeout enforcement
    - Structured error handling
    - Metrics instrumentation
    - Safe resource cleanup
    """

    def __init__(
        self,
        *,
        url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        query_timeout: int = 30,
        echo: bool = False,
    ) -> None:
        self._validate_connection_url(url)

        # Translate libpq sslmode -> asyncpg ssl kwarg. The Vault DSN
        # carries sslmode=require (Tier 11 mandate, enforced by
        # Settings._validate_production_secrets BEFORE this constructor
        # runs), but asyncpg's connect() rejects sslmode as an unknown
        # kwarg. Strip + translate to ssl='require' in connect_args.
        # See _translate_sslmode_for_asyncpg docstring for the full
        # libpq -> asyncpg mapping table.
        cleaned_url, ssl_kwarg = _translate_sslmode_for_asyncpg(url)

        connect_args: dict[str, Any] = {"server_settings": {"statement_timeout": str(query_timeout * 1000)}}
        if ssl_kwarg is not None:
            connect_args["ssl"] = ssl_kwarg

        self._query_timeout = query_timeout
        self._engine: AsyncEngine = create_async_engine(
            cleaned_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            echo=echo,
            connect_args=connect_args,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self._setup_event_listeners()

        logger.info(
            "database_manager_initialized",
            extra={
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "query_timeout": query_timeout,
            },
        )

    @staticmethod
    def _validate_connection_url(url: str) -> None:
        """Validate database connection URL format and security."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                raise ValueError("Missing database scheme")
            if not parsed.hostname:
                raise ValueError("Missing database hostname")
            if parsed.scheme not in ("postgresql+asyncpg", "postgresql+psycopg"):
                logger.warning(
                    "unsupported_db_scheme",
                    extra={"scheme": parsed.scheme},
                )
        except Exception as e:
            logger.error("invalid_connection_url", extra={"error": str(e)})
            raise DatabaseConnectionError(f"Invalid connection URL: {e}") from e

    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for monitoring."""

        @event.listens_for(self._engine.sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug("db_connection_established")

        @event.listens_for(self._engine.sync_engine, "close")
        def receive_close(dbapi_conn, connection_record):
            logger.debug("db_connection_closed")

    @property
    def engine(self) -> AsyncEngine:
        """Get underlying SQLAlchemy async engine."""
        return self._engine

    @asynccontextmanager
    async def session(
        self,
        *,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> AsyncIterator[AsyncSession]:
        """
        Transactional write session with automatic commit/rollback.

        Args:
            trace_id: Distributed trace ID for correlation
            idempotency_key: Optional idempotency key for duplicate detection

        Yields:
            AsyncSession: Database session

        Raises:
            DatabaseIntegrityError: On constraint violations
            DatabaseOperationalError: On connection/operational failures
            DatabaseTimeoutError: On query timeout
        """
        start_time = asyncio.get_event_loop().time()

        async with self._session_factory() as session:
            try:
                if idempotency_key:
                    session.info["idempotency_key"] = idempotency_key
                if trace_id:
                    session.info["trace_id"] = trace_id

                yield session
                await session.commit()

                duration = asyncio.get_event_loop().time() - start_time
                DB_OPERATION_DURATION.labels(operation="write").observe(duration)

                logger.debug(
                    "db_transaction_committed",
                    extra={
                        "trace_id": trace_id,
                        "duration_ms": round(duration * 1000, 2),
                    },
                )

            except IntegrityError as e:
                await session.rollback()
                DB_OPERATION_ERRORS.labels(operation="write", error_type="integrity").inc()
                logger.warning(
                    "db_integrity_error",
                    extra={
                        "trace_id": trace_id,
                        "error": str(e.orig) if hasattr(e, "orig") else str(e),
                    },
                )
                raise DatabaseIntegrityError(str(e)) from e

            except (OperationalError, DBAPIError) as e:
                await session.rollback()
                DB_OPERATION_ERRORS.labels(operation="write", error_type="operational").inc()
                logger.error(
                    "db_operational_error",
                    extra={
                        "trace_id": trace_id,
                        "error": str(e.orig) if hasattr(e, "orig") else str(e),
                    },
                )
                raise DatabaseOperationalError(str(e)) from e

            except SQLAlchemyTimeoutError as e:
                await session.rollback()
                DB_OPERATION_ERRORS.labels(operation="write", error_type="timeout").inc()
                logger.error(
                    "db_timeout_error",
                    extra={
                        "trace_id": trace_id,
                        "timeout_seconds": self._query_timeout,
                    },
                )
                raise DatabaseTimeoutError(f"Query exceeded timeout of {self._query_timeout}s") from e

            except Exception:
                await session.rollback()
                DB_OPERATION_ERRORS.labels(operation="write", error_type="unknown").inc()
                logger.exception(
                    "db_unexpected_error",
                    extra={"trace_id": trace_id},
                )
                raise

    @asynccontextmanager
    async def read_session(
        self,
        *,
        trace_id: str | None = None,
    ) -> AsyncIterator[AsyncSession]:
        """
        Read-only session (no automatic commit).

        Args:
            trace_id: Distributed trace ID for correlation

        Yields:
            AsyncSession: Database session
        """
        start_time = asyncio.get_event_loop().time()

        async with self._session_factory() as session:
            try:
                if trace_id:
                    session.info["trace_id"] = trace_id

                yield session

                duration = asyncio.get_event_loop().time() - start_time
                DB_OPERATION_DURATION.labels(operation="read").observe(duration)

            except Exception:
                DB_OPERATION_ERRORS.labels(operation="read", error_type="unknown").inc()
                logger.exception(
                    "db_read_error",
                    extra={"trace_id": trace_id},
                )
                raise

    async def health_check(self) -> bool:
        """
        Check database connectivity with retry logic.

        Returns:
            bool: True if healthy, False otherwise
        """
        max_retries = 3
        base_delay = 0.1

        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    async with self._engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))

                logger.debug("db_health_check_passed")
                return True

            except TimeoutError:
                logger.warning(
                    "db_health_check_timeout",
                    extra={"attempt": attempt + 1},
                )

            except Exception as e:
                logger.warning(
                    "db_health_check_failed",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                )

            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt) * (1 + asyncio.get_event_loop().time() % 0.1)
                await asyncio.sleep(delay)

        logger.error("db_health_check_exhausted")
        return False

    def update_pool_metrics(self) -> None:
        """Update Prometheus metrics for connection pool state."""
        try:
            pool = self._engine.pool
            if isinstance(pool, QueuePool):
                DB_CONNECTION_POOL_SIZE.labels(state="checked_in").set(pool.checkedin())
                DB_CONNECTION_POOL_SIZE.labels(state="checked_out").set(pool.checkedout())
                DB_CONNECTION_POOL_SIZE.labels(state="overflow").set(pool.overflow())
        except Exception:
            logger.exception("pool_metrics_update_failed")

    async def close(self) -> None:
        """Gracefully close all database connections."""
        try:
            await self._engine.dispose()
            logger.info("database_manager_closed")
        except Exception:
            logger.exception("database_close_failed")
            raise
