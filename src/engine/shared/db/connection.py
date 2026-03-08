from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from urllib.parse import urlparse

from sqlalchemy import event, text
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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
        
        self._query_timeout = query_timeout
        self._engine: AsyncEngine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            echo=echo,
            connect_args={
                "server_settings": {"statement_timeout": str(query_timeout * 1000)},
            },
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
        trace_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
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
                raise DatabaseTimeoutError(
                    f"Query exceeded timeout of {self._query_timeout}s"
                ) from e
                
            except Exception as e:
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
        trace_id: Optional[str] = None,
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
                
            except Exception as e:
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
                
            except asyncio.TimeoutError:
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
                delay = base_delay * (2 ** attempt) * (1 + asyncio.get_event_loop().time() % 0.1)
                await asyncio.sleep(delay)
        
        logger.error("db_health_check_exhausted")
        return False

    def update_pool_metrics(self) -> None:
        """Update Prometheus metrics for connection pool state."""
        try:
            pool = self._engine.pool
            if pool is not None:
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
