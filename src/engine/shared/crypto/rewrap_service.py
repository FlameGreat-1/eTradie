"""Credential re-wrap maintenance service (KEK rotation / revocation).

Executes a key rotation by upgrading every stored credential ciphertext
to the ACTIVE KEK version, using the shared envelope cipher's
``needs_rewrap`` / ``rewrap_credential`` primitives. The plaintext
credential is never altered -- only the envelope protecting it is
re-wrapped under the active KEK -- so this is safe to run against live
broker + LLM credentials.

Operational model
-----------------
1. Operator adds a new KEK version (BROKER_ENCRYPTION_KEY_V<n>) via the
   engine ExternalSecret (helm rotationKeyVersions). Pods restart; the
   shared cipher now treats version <n> as the ACTIVE write key while
   still holding the previous version for decryption.
2. Operator runs this service (one-shot Job: ``python -m
   engine.shared.crypto.rewrap_service``). Every row is decrypted with
   whatever version applies and re-encrypted under version <n>;
   ``key_version`` is updated to <n>.
3. Once the run reports 0 remaining rows on old versions, the operator
   REMOVES the old KEK version from Vault + rotationKeyVersions to
   REVOKE it. No ciphertext references it any more.

The legacy (pre-envelope) ciphertext upgrade is the same flow: a NULL /
legacy row is decrypted with the base KEK and re-wrapped to the active
version, so the first run after this feature ships also migrates every
pre-existing credential onto the envelope format.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text

from engine.shared.crypto.credential_cipher import (
    active_key_version,
    needs_rewrap,
    rewrap_credential,
)
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class _Target:
    """One credential table and the encrypted columns it carries."""

    table: str
    id_column: str
    encrypted_columns: tuple[str, ...]
    key_version_column: str = "key_version"


# The two credential stores and their encrypted columns. Single source
# of truth so broker + LLM share one rotation code path. Adding a future
# credential column is a one-line change here.
_TARGETS: tuple[_Target, ...] = (
    _Target(
        table="broker_connections",
        id_column="id",
        encrypted_columns=("mt5_password_encrypted", "ea_auth_token_encrypted"),
    ),
    _Target(
        table="llm_connections",
        id_column="id",
        encrypted_columns=("api_key_encrypted",),
    ),
)


@dataclass
class RewrapStats:
    """Outcome of a re-wrap run, per table and in aggregate."""

    active_version: int
    scanned_rows: int = 0
    rewrapped_columns: int = 0
    rewrapped_rows: int = 0
    failed_columns: int = 0
    per_table: dict[str, dict[str, int]] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "active_version": self.active_version,
            "scanned_rows": self.scanned_rows,
            "rewrapped_rows": self.rewrapped_rows,
            "rewrapped_columns": self.rewrapped_columns,
            "failed_columns": self.failed_columns,
            "per_table": self.per_table,
        }


class CredentialRewrapService:
    """Re-wraps stored credentials onto the active KEK version."""

    def __init__(self, db: DatabaseManager, *, batch_size: int = 200) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self._db = db
        self._batch_size = batch_size

    async def run(self, *, dry_run: bool = False) -> RewrapStats:
        """Re-wrap every credential not already on the active KEK version.

        When ``dry_run`` is True, no write happens; the stats report how
        many columns/rows WOULD be re-wrapped (for pre-rotation sizing).
        """
        active = active_key_version()
        stats = RewrapStats(active_version=active)

        logger.info(
            "credential_rewrap_started",
            extra={"active_version": active, "dry_run": dry_run},
        )

        for target in _TARGETS:
            table_stats = await self._run_target(target, dry_run=dry_run, stats=stats)
            stats.per_table[target.table] = table_stats

        logger.info(
            "credential_rewrap_completed",
            extra={"dry_run": dry_run, **stats.as_dict()},
        )
        return stats

    async def _run_target(
        self,
        target: _Target,
        *,
        dry_run: bool,
        stats: RewrapStats,
    ) -> dict[str, int]:
        """Process one credential table in keyset-paginated batches."""
        table_stats = {"scanned_rows": 0, "rewrapped_rows": 0, "rewrapped_columns": 0, "failed_columns": 0}
        col_list = ", ".join((target.id_column, *target.encrypted_columns))
        cursor: Optional[str] = None

        while True:
            rows = await self._fetch_batch(target, col_list, cursor)
            if not rows:
                break

            for row in rows:
                cursor = str(row[target.id_column])
                stats.scanned_rows += 1
                table_stats["scanned_rows"] += 1
                await self._process_row(
                    target, row, dry_run=dry_run, stats=stats, table_stats=table_stats
                )

            if len(rows) < self._batch_size:
                break

        return table_stats

    async def _fetch_batch(
        self,
        target: _Target,
        col_list: str,
        cursor: Optional[str],
    ) -> list[dict]:
        """Read one keyset page ordered by id (stable, memory-bounded)."""
        where = "" if cursor is None else f"WHERE {target.id_column} > :cursor"
        sql = (
            f"SELECT {col_list} FROM {target.table} "  # noqa: S608 - table/cols are module constants, not user input
            f"{where} ORDER BY {target.id_column} ASC LIMIT :limit"
        )
        params: dict = {"limit": self._batch_size}
        if cursor is not None:
            params["cursor"] = cursor
        async with self._db.read_session() as session:
            result = await session.execute(text(sql), params)
            return [dict(m) for m in result.mappings().all()]

    async def _process_row(
        self,
        target: _Target,
        row: dict,
        *,
        dry_run: bool,
        stats: RewrapStats,
        table_stats: dict[str, int],
    ) -> None:
        """Re-wrap any stale encrypted column on a single row.

        Each row is its own committed transaction so an interrupted run
        leaves only unprocessed rows for the next run (resumable). A
        per-column failure is logged + counted but never aborts the run.
        """
        row_id = row[target.id_column]
        updates: dict[str, str] = {}

        for col in target.encrypted_columns:
            ciphertext = row.get(col)
            if not ciphertext:
                continue  # NULL column (no secret stored) -- nothing to do.
            try:
                if not needs_rewrap(ciphertext):
                    continue
                if dry_run:
                    # Count what WOULD change without producing new ct.
                    stats.rewrapped_columns += 1
                    table_stats["rewrapped_columns"] += 1
                    continue
                updates[col] = rewrap_credential(ciphertext)
            except Exception as exc:  # noqa: BLE001 - isolate per-column failure
                stats.failed_columns += 1
                table_stats["failed_columns"] += 1
                logger.error(
                    "credential_rewrap_column_failed",
                    extra={
                        "table": target.table,
                        "row_id": str(row_id),
                        "column": col,
                        "error": str(exc),
                    },
                )

        if dry_run or not updates:
            return

        await self._persist_row(target, row_id, updates)
        stats.rewrapped_rows += 1
        table_stats["rewrapped_rows"] += 1
        stats.rewrapped_columns += len(updates)
        table_stats["rewrapped_columns"] += len(updates)
        logger.info(
            "credential_rewrap_row_rewrapped",
            extra={
                "table": target.table,
                "row_id": str(row_id),
                "columns": list(updates.keys()),
                "active_version": stats.active_version,
            },
        )

    async def _persist_row(
        self,
        target: _Target,
        row_id: object,
        updates: dict[str, str],
    ) -> None:
        """UPDATE the re-wrapped columns + key_version for one row."""
        set_clauses = [f"{col} = :{col}" for col in updates]
        set_clauses.append(f"{target.key_version_column} = :__key_version")
        sql = (
            f"UPDATE {target.table} SET {', '.join(set_clauses)} "  # noqa: S608 - identifiers are module constants
            f"WHERE {target.id_column} = :__row_id"
        )
        params: dict = dict(updates)
        params["__key_version"] = active_key_version()
        params["__row_id"] = row_id
        async with self._db.session() as session:
            await session.execute(text(sql), params)
