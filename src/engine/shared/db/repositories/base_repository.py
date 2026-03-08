from __future__ import annotations

import time
from typing import Any, Generic, Sequence, TypeVar, Optional

from sqlalchemy import Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from engine.shared.exceptions import (
    DatabaseIntegrityError,
    DatabaseOperationalError,
    RepositoryError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    DB_QUERY_DURATION,
    DB_QUERY_ERRORS,
    DB_QUERY_ROWS,
)

logger = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=DeclarativeBase)

# Security: Maximum pagination limits to prevent resource exhaustion
MAX_QUERY_LIMIT = 1000
DEFAULT_QUERY_LIMIT = 100


class BaseRepository(Generic[ModelT]):
    """
    Production-grade base repository with type safety, metrics, and error handling.
    
    Provides:
    - CRUD operations with proper error handling
    - Bulk operations with conflict resolution
    - Query metrics and observability
    - Input validation and security controls
    - Idempotent upsert operations
    """
    
    model: type[ModelT]
    _repo_name: str = "base"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _get_trace_id(self) -> Optional[str]:
        """Extract trace_id from session context if available."""
        return self._session.info.get("trace_id")

    def _observe_query(
        self,
        operation: str,
        start: float,
        row_count: Optional[int] = None,
    ) -> None:
        """Record query metrics."""
        duration = time.monotonic() - start
        
        DB_QUERY_DURATION.labels(
            repository=self._repo_name,
            operation=operation,
        ).observe(duration)
        
        if row_count is not None:
            DB_QUERY_ROWS.labels(
                repository=self._repo_name,
                operation=operation,
            ).observe(row_count)
        
        logger.debug(
            "repository_query_executed",
            extra={
                "repository": self._repo_name,
                "operation": operation,
                "duration_ms": round(duration * 1000, 2),
                "row_count": row_count,
                "trace_id": self._get_trace_id(),
            },
        )

    def _observe_error(self, operation: str, error_type: str) -> None:
        """Record query error metrics."""
        DB_QUERY_ERRORS.labels(
            repository=self._repo_name,
            operation=operation,
            error_type=error_type,
        ).inc()

    def _validate_pagination(self, offset: int, limit: int) -> tuple[int, int]:
        """
        Validate and sanitize pagination parameters.
        
        Args:
            offset: Query offset
            limit: Query limit
            
        Returns:
            Validated (offset, limit) tuple
            
        Raises:
            RepositoryError: On invalid pagination parameters
        """
        if offset < 0:
            raise RepositoryError("Offset must be non-negative")
        
        if limit < 1:
            raise RepositoryError("Limit must be positive")
        
        if limit > MAX_QUERY_LIMIT:
            logger.warning(
                "pagination_limit_exceeded",
                extra={
                    "requested_limit": limit,
                    "max_limit": MAX_QUERY_LIMIT,
                    "trace_id": self._get_trace_id(),
                },
            )
            limit = MAX_QUERY_LIMIT
        
        return offset, limit

    async def get_by_id(self, record_id: Any) -> ModelT | None:
        """
        Retrieve a single record by primary key.
        
        Args:
            record_id: Primary key value
            
        Returns:
            Model instance or None if not found
            
        Raises:
            DatabaseOperationalError: On database errors
        """
        start = time.monotonic()
        
        try:
            result = await self._session.get(self.model, record_id)
            self._observe_query("get_by_id", start, row_count=1 if result else 0)
            return result
            
        except OperationalError as e:
            self._observe_error("get_by_id", "operational")
            logger.error(
                "repository_get_failed",
                extra={
                    "repository": self._repo_name,
                    "record_id": record_id,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = DEFAULT_QUERY_LIMIT,
    ) -> Sequence[ModelT]:
        """
        List records with pagination.
        
        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Sequence of model instances
            
        Raises:
            RepositoryError: On invalid pagination parameters
            DatabaseOperationalError: On database errors
        """
        offset, limit = self._validate_pagination(offset, limit)
        start = time.monotonic()
        
        try:
            stmt = select(self.model).offset(offset).limit(limit)
            result = await self._session.execute(stmt)
            rows = result.scalars().all()
            self._observe_query("list_all", start, row_count=len(rows))
            return rows
            
        except OperationalError as e:
            self._observe_error("list_all", "operational")
            logger.error(
                "repository_list_failed",
                extra={
                    "repository": self._repo_name,
                    "offset": offset,
                    "limit": limit,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def add(self, instance: ModelT) -> ModelT:
        """
        Add a single record.
        
        Args:
            instance: Model instance to add
            
        Returns:
            Added model instance with generated fields populated
            
        Raises:
            DatabaseIntegrityError: On constraint violations
            DatabaseOperationalError: On database errors
        """
        start = time.monotonic()
        
        try:
            self._session.add(instance)
            await self._session.flush()
            self._observe_query("add", start, row_count=1)
            return instance
            
        except IntegrityError as e:
            self._observe_error("add", "integrity")
            logger.warning(
                "repository_add_integrity_error",
                extra={
                    "repository": self._repo_name,
                    "error": str(e.orig) if hasattr(e, "orig") else str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseIntegrityError(str(e)) from e
            
        except OperationalError as e:
            self._observe_error("add", "operational")
            logger.error(
                "repository_add_failed",
                extra={
                    "repository": self._repo_name,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def add_many(self, instances: Sequence[ModelT]) -> int:
        """
        Add multiple records in a single operation.
        
        Args:
            instances: Sequence of model instances to add
            
        Returns:
            Number of records added
            
        Raises:
            DatabaseIntegrityError: On constraint violations
            DatabaseOperationalError: On database errors
        """
        if not instances:
            return 0
        
        start = time.monotonic()
        count = len(instances)
        
        try:
            self._session.add_all(instances)
            await self._session.flush()
            self._observe_query("add_many", start, row_count=count)
            return count
            
        except IntegrityError as e:
            self._observe_error("add_many", "integrity")
            logger.warning(
                "repository_add_many_integrity_error",
                extra={
                    "repository": self._repo_name,
                    "count": count,
                    "error": str(e.orig) if hasattr(e, "orig") else str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseIntegrityError(str(e)) from e
            
        except OperationalError as e:
            self._observe_error("add_many", "operational")
            logger.error(
                "repository_add_many_failed",
                extra={
                    "repository": self._repo_name,
                    "count": count,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def upsert(
        self,
        values: dict[str, Any],
        *,
        index_elements: list[str],
        update_fields: list[str] | None = None,
    ) -> None:
        """
        Insert or update a single record (idempotent operation).
        
        Args:
            values: Field values to insert/update
            index_elements: Columns to use for conflict detection
            update_fields: Fields to update on conflict (None = do nothing)
            
        Raises:
            DatabaseOperationalError: On database errors
        """
        start = time.monotonic()
        idempotency_key = self._session.info.get("idempotency_key")
        
        try:
            stmt = pg_insert(self.model).values(**values)
            
            if update_fields:
                update_dict = {f: stmt.excluded[f] for f in update_fields}
                stmt = stmt.on_conflict_do_update(
                    index_elements=index_elements,
                    set_=update_dict,
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
            
            await self._session.execute(stmt)
            await self._session.flush()
            self._observe_query("upsert", start, row_count=1)
            
            logger.debug(
                "repository_upsert_executed",
                extra={
                    "repository": self._repo_name,
                    "index_elements": index_elements,
                    "update_fields": update_fields,
                    "idempotency_key": idempotency_key,
                    "trace_id": self._get_trace_id(),
                },
            )
            
        except OperationalError as e:
            self._observe_error("upsert", "operational")
            logger.error(
                "repository_upsert_failed",
                extra={
                    "repository": self._repo_name,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def bulk_upsert(
        self,
        rows: list[dict[str, Any]],
        *,
        index_elements: list[str],
        update_fields: list[str] | None = None,
    ) -> int:
        """
        Insert or update multiple records in a single operation (idempotent).
        
        Args:
            rows: List of field value dictionaries
            index_elements: Columns to use for conflict detection
            update_fields: Fields to update on conflict (None = do nothing)
            
        Returns:
            Number of rows affected
            
        Raises:
            DatabaseOperationalError: On database errors
        """
        if not rows:
            return 0
        
        start = time.monotonic()
        count = len(rows)
        
        try:
            stmt = pg_insert(self.model).values(rows)
            
            if update_fields:
                update_dict = {f: stmt.excluded[f] for f in update_fields}
                stmt = stmt.on_conflict_do_update(
                    index_elements=index_elements,
                    set_=update_dict,
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
            
            result = await self._session.execute(stmt)
            await self._session.flush()
            
            row_count = result.rowcount or 0
            self._observe_query("bulk_upsert", start, row_count=row_count)
            
            logger.debug(
                "repository_bulk_upsert_executed",
                extra={
                    "repository": self._repo_name,
                    "input_rows": count,
                    "affected_rows": row_count,
                    "index_elements": index_elements,
                    "trace_id": self._get_trace_id(),
                },
            )
            
            return row_count
            
        except OperationalError as e:
            self._observe_error("bulk_upsert", "operational")
            logger.error(
                "repository_bulk_upsert_failed",
                extra={
                    "repository": self._repo_name,
                    "count": count,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def delete_by_id(self, record_id: Any) -> bool:
        """
        Delete a record by primary key.
        
        Args:
            record_id: Primary key value
            
        Returns:
            True if record was deleted, False if not found
            
        Raises:
            DatabaseOperationalError: On database errors
        """
        start = time.monotonic()
        
        try:
            stmt = delete(self.model).where(self.model.id == record_id)  # type: ignore[attr-defined]
            result = await self._session.execute(stmt)
            await self._session.flush()
            
            deleted = (result.rowcount or 0) > 0
            self._observe_query("delete_by_id", start, row_count=1 if deleted else 0)
            
            return deleted
            
        except OperationalError as e:
            self._observe_error("delete_by_id", "operational")
            logger.error(
                "repository_delete_failed",
                extra={
                    "repository": self._repo_name,
                    "record_id": record_id,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def count(self, stmt: Select[Any] | None = None) -> int:
        """
        Count records matching optional query.
        
        Args:
            stmt: Optional SELECT statement to count (None = count all)
            
        Returns:
            Record count
            
        Raises:
            DatabaseOperationalError: On database errors
        """
        start = time.monotonic()
        
        try:
            if stmt is None:
                count_stmt = select(func.count()).select_from(self.model)
            else:
                count_stmt = select(func.count()).select_from(stmt.subquery())
            
            result = await self._session.execute(count_stmt)
            count = result.scalar_one()
            self._observe_query("count", start)
            
            return count
            
        except OperationalError as e:
            self._observe_error("count", "operational")
            logger.error(
                "repository_count_failed",
                extra={
                    "repository": self._repo_name,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e

    async def execute_query(self, stmt: Select[Any]) -> Sequence[ModelT]:
        """
        Execute a custom SELECT query.
        
        Args:
            stmt: SELECT statement to execute
            
        Returns:
            Sequence of model instances
            
        Raises:
            DatabaseOperationalError: On database errors
        """
        start = time.monotonic()
        
        try:
            result = await self._session.execute(stmt)
            rows = result.scalars().all()
            self._observe_query("execute_query", start, row_count=len(rows))
            
            return rows
            
        except OperationalError as e:
            self._observe_error("execute_query", "operational")
            logger.error(
                "repository_query_failed",
                extra={
                    "repository": self._repo_name,
                    "error": str(e),
                    "trace_id": self._get_trace_id(),
                },
            )
            raise DatabaseOperationalError(str(e)) from e
