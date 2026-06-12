from __future__ import annotations

from datetime import UTC
from datetime import datetime as dt

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.exceptions import AuthUserMissingError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Name of the FK constraint from billing_usage.user_id ->
# auth_users.id. Defined in src/billing/store/schema.go. Matching on
# the constraint name (rather than substring-sniffing the SQLSTATE
# message) keeps the detector resilient to wording changes in asyncpg
# / PostgreSQL and avoids misfiring on unrelated FKs.
_AUTH_USERS_FK_CONSTRAINT = "billing_usage_user_id_fkey"


def _is_auth_users_fk_violation(exc: BaseException) -> bool:
    """Return True iff ``exc`` is a FK violation against ``auth_users``.

    SQLAlchemy wraps the underlying asyncpg ForeignKeyViolationError
    inside an ``IntegrityError`` whose ``.orig`` carries the original
    asyncpg exception. asyncpg exposes the violated constraint name on
    ``constraint_name``; we check that first and fall back to a string
    match on the error text so the detector still works when only the
    stringified form is available (e.g. when the exception has already
    been re-wrapped by the engine's DatabaseManager).
    """
    orig = getattr(exc, "orig", None) or exc
    constraint = getattr(orig, "constraint_name", "") or ""
    if constraint == _AUTH_USERS_FK_CONSTRAINT:
        return True
    return _AUTH_USERS_FK_CONSTRAINT in str(exc)


class BillingRepository:
    """Manages billing_usage table for tracking usage quotas."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_or_create_usage(self, user_id: str) -> dict:
        """Get the user's usage, creating a new row if none exists.

        Raises:
            AuthUserMissingError: when ``user_id`` is not present in
                ``auth_users``. This happens when a still-valid JWT
                outlives the row it references (e.g. admin deleted
                the user, or the gateway and engine drifted to
                different databases in dev). Callers should map this
                to HTTP 401 so the SPA logs the user out.
        """
        # Ensure we reset daily limits if last_reset_at was yesterday
        # We handle the day check in Python logic for simplicity
        stmt = text("""
            INSERT INTO billing_usage (user_id)
            VALUES (:user_id)
            ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
            RETURNING analyses_today, llm_tokens_used, execution_attempts, watcher_count, last_reset_at
            """)
        try:
            res = await self._session.execute(stmt, {"user_id": user_id})
            row = res.mappings().first()
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if _is_auth_users_fk_violation(exc):
                logger.warning(
                    "billing_usage_orphan_user_id",
                    extra={"user_id": user_id, "constraint": _AUTH_USERS_FK_CONSTRAINT},
                )
                raise AuthUserMissingError(user_id) from exc
            raise
        return dict(row) if row else {}

    async def reset_daily_usage_if_needed(self, user_id: str):
        """Reset analyses_today if last_reset_at is not today."""
        usage = await self.get_or_create_usage(user_id)
        last_reset = usage.get("last_reset_at")

        if last_reset:
            now = dt.now(UTC)
            # If the calendar day has changed
            if last_reset.date() != now.date():
                stmt = text("""
                    UPDATE billing_usage
                    SET analyses_today = 0, last_reset_at = NOW()
                    WHERE user_id = :user_id
                    """)
                await self._session.execute(stmt, {"user_id": user_id})
                await self._session.commit()

    async def increment_analysis(self, user_id: str):
        """Increment the analyses_today count and record the timestamp atomically."""
        stmt = text("""
            UPDATE billing_usage
            SET analyses_today = CASE
                    WHEN DATE(last_reset_at) < CURRENT_DATE THEN 1
                    ELSE analyses_today + 1
                END,
                last_reset_at = CASE
                    WHEN DATE(last_reset_at) < CURRENT_DATE THEN NOW()
                    ELSE last_reset_at
                END,
                last_analysis_at = NOW()
            WHERE user_id = :user_id
            """)
        await self._session.execute(stmt, {"user_id": user_id})
        await self._session.commit()

    async def get_usage_for_user(self, user_id: str) -> dict:
        """Return the full usage row for a user (for the dashboard countdown)."""
        stmt = text("""
            SELECT analyses_today, llm_tokens_used, ta_cycles_used,
                   macro_cycles_used, execution_attempts, watcher_count,
                   last_analysis_at, last_reset_at
            FROM billing_usage
            WHERE user_id = :user_id
            """)
        res = await self._session.execute(stmt, {"user_id": user_id})
        row = res.mappings().first()
        if not row:
            return {}
        result = dict(row)
        # Convert datetimes to ISO strings for JSON serialization.
        for key in ("last_analysis_at", "last_reset_at"):
            if result.get(key) is not None:
                result[key] = result[key].isoformat()
        return result

    async def increment_tokens(self, user_id: str, tokens: int):
        """Add tokens to the user's running total."""
        stmt = text("""
            UPDATE billing_usage
            SET llm_tokens_used = llm_tokens_used + :tokens
            WHERE user_id = :user_id
            """)
        await self._session.execute(stmt, {"user_id": user_id, "tokens": tokens})
        await self._session.commit()

    async def increment_usage_metric(self, user_id: str, column: str, amount: int = 1):
        """Increment a specific usage metric column (e.g., ta_cycles_used)."""
        # Validate column name to prevent SQL injection
        allowed = {
            "ta_cycles_used",
            "macro_cycles_used",
            "execution_attempts",
            "llm_tokens_used",
            "analyses_today",
            "watcher_count",
        }
        if column not in allowed:
            return

        stmt = text(f"""
            UPDATE billing_usage
            SET {column} = {column} + :amount
            WHERE user_id = :user_id
            """)
        await self._session.execute(stmt, {"user_id": user_id, "amount": amount})
        await self._session.commit()
