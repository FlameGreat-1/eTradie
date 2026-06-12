"""One-shot CLI to re-wrap stored credentials onto the active KEK version.

Usage (as a Kubernetes Job or `kubectl exec` on an engine pod, which
already has the engine env + Vault-sourced KEKs):

    python -m engine.shared.crypto              # execute
    python -m engine.shared.crypto --dry-run    # report only
    python -m engine.shared.crypto --batch-size 500

Exit codes:
    0  success (including a no-op run with nothing to re-wrap)
    2  completed but one or more columns failed to re-wrap
    1  fatal/setup error (config, DB connect, etc.)

This module is intentionally tiny: all logic lives in
CredentialRewrapService. It only wires the engine settings into a
DatabaseManager and translates the run outcome into a process exit code.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from engine.config import get_settings
from engine.shared.crypto.rewrap_service import CredentialRewrapService
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger

logger = get_logger(__name__)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="engine.shared.crypto.rewrap_service",
        description="Re-wrap stored credentials onto the active KEK version (Tier 3 key rotation).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many columns/rows would be re-wrapped without writing.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Keyset page size for table scans (default: 200).",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    db = DatabaseManager(
        url=settings.async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        echo=settings.db_echo,
    )
    try:
        service = CredentialRewrapService(db, batch_size=args.batch_size)
        stats = await service.run(dry_run=args.dry_run)
    finally:
        await db.close()

    print(json.dumps(stats.as_dict(), indent=2))

    if stats.failed_columns > 0:
        logger.error(
            "credential_rewrap_completed_with_failures",
            extra={"failed_columns": stats.failed_columns},
        )
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return asyncio.run(_run(args))
    except Exception as exc:  # noqa: BLE001 - top-level CLI guard
        logger.error("credential_rewrap_fatal", extra={"error": str(exc)})
        print(f"credential re-wrap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
