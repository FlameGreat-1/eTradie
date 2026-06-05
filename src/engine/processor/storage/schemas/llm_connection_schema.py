"""SQLAlchemy table definition for LLM connection persistence.

Stores user-configured LLM provider connections with API keys.

Uniqueness invariant (enforced at the DB level by Alembic 0022 and
mirrored here for the test/dev `create_all` install path):

  * Personal scope (is_platform=false, user_id=<uuid>) -- at most one
    row with is_active = true per user. Enforced by the partial
    unique index ``uq_llm_connections_one_active_personal_per_user``.

  * Platform scope (is_platform=true, user_id=NULL) -- at most one
    row with is_active = true globally. Enforced by the partial
    unique index ``uq_llm_connections_one_active_platform`` (uniqueness
    on the constant `true`).

The repository's ``activate`` / ``create`` paths additionally take a
row-level lock on the user's existing rows so concurrent transactions
serialise on the happy path instead of racing past the unique index
and returning IntegrityError to the caller.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.processor.storage.schemas.processor_schema import ProcessorBase


class LLMConnectionRow(ProcessorBase):
    """Persisted LLM provider connection configured by the user."""

    __tablename__ = "llm_connections"

    # -- DB-level uniqueness for the "one active per scope" invariant. --
    # Mirrors the indexes created by Alembic migration 0022. Listed in
    # __table_args__ so SQLAlchemy's metadata.create_all() (used by the
    # test fixtures and the dev container's first-run bootstrap) also
    # installs them, keeping the migration path and the create_all path
    # behaviourally identical.
    __table_args__ = (
        Index(
            "uq_llm_connections_one_active_personal_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active = true AND is_platform = false"),
        ),
        Index(
            "uq_llm_connections_one_active_platform",
            "is_platform",
            unique=True,
            postgresql_where=text("is_active = true AND is_platform = true"),
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # -- Owner (multi-tenant isolation) ----------------------------------------
    # References auth_users.id managed by the Go auth service.
    # Every query MUST filter by user_id to enforce data ownership.
    user_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    is_platform: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    api_key_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # KEK version that wrapped the CURRENT api_key_encrypted ciphertext
    # (envelope encryption, engine.shared.crypto). NULL means legacy
    # pre-envelope ciphertext / unknown version; operational metadata
    # only, never load-bearing for decryption. See migration 0033.
    key_version: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    base_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
    )
    max_output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="32768",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
    )
    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
