from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Schema imports — Alembic needs these so table metadata registers on
# Base.metadata. Each package's __init__.py re-exports every schema
# module via `from ... import *` so importing the package alone is
# enough. Adding a NEW model package? Append it here AND ensure its
# __init__.py re-exports each module so Base.metadata is populated.
# Audit ref: FV-M1.
import engine.macro.storage.schemas  # noqa: F401
import engine.processor.storage.schemas  # noqa: F401
import engine.rag.storage.schemas  # noqa: F401
import engine.ta.storage.schemas  # noqa: F401
from engine.config import get_settings
from engine.shared.db.migrations._schema_registry import Base  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()

# Translate libpq's `sslmode` query param to asyncpg's `ssl` kwarg.
# Mirror of engine.shared.db.connection._translate_sslmode_for_asyncpg —
# kept inline so the migrate init does not import the heavier
# DatabaseManager module path (which would pull in Prometheus client +
# logging + metrics modules just to run a one-shot alembic migration).
#
# Two modes (selected by ENGINE_DB_NATIVE_TLS env var, default false):
#
#   MESH (default): asyncpg ssl=False regardless of sslmode. Linkerd
#     encrypts the wire; postgres in-cluster serves plaintext. asyncpg
#     must not attempt a server-side TLS upgrade.
#
#   NATIVE (opt-in): libpq sslmode -> asyncpg ssl mapping (require ->
#     'require', verify-ca -> 'verify-ca', verify-full -> 'verify-full').
#     For managed-postgres deployments (Neon / RDS / Cloud SQL) where
#     the server serves real TLS.
#
# Settings._validate_production_secrets still requires sslmode in
# {require, verify-ca, verify-full} in the URL string — that is the
# Tier 11 audit-trail invariant on configuration intent, unchanged in
# both modes.
_LIBPQ_SSLMODE_TO_ASYNCPG_SSL_NATIVE: dict[str, Any] = {
    "disable": False,
    "require": "require",
    "verify-ca": "verify-ca",
    "verify-full": "verify-full",
}


def _engine_db_native_tls() -> bool:
    return os.environ.get("ENGINE_DB_NATIVE_TLS", "false").strip().lower() in {"1", "true", "yes", "on"}


def _translate_sslmode(url: str) -> tuple[str, Any]:
    parsed = urlparse(url)
    if not parsed.query:
        return url, None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    kept: list[tuple[str, str]] = []
    sslmode_value: str | None = None
    for k, v in pairs:
        if k.lower() == "sslmode":
            sslmode_value = v
            continue
        kept.append((k, v))
    if sslmode_value is None:
        return url, None
    cleaned = urlunparse(parsed._replace(query=urlencode(kept, doseq=True)))
    if not _engine_db_native_tls():
        # MESH mode: Linkerd encrypts the wire; asyncpg ssl off.
        return cleaned, False
    return cleaned, _LIBPQ_SSLMODE_TO_ASYNCPG_SSL_NATIVE.get(sslmode_value.strip().lower())


_raw_url = settings.async_database_url
_cleaned_url, _ssl_kwarg = _translate_sslmode(_raw_url)
config.set_main_option("sqlalchemy.url", _cleaned_url)
_engine_connect_args: dict[str, Any] = {}
if _ssl_kwarg is not None:
    _engine_connect_args["ssl"] = _ssl_kwarg


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # async_engine_from_config forwards the kwargs we add here into
    # SQLAlchemy's create_async_engine call. connect_args carries the
    # asyncpg `ssl` kwarg derived from the URL's original sslmode by
    # _translate_sslmode above. If sslmode was absent (dev/testing), the
    # dict is empty and asyncpg uses its default (no TLS).
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_engine_connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
