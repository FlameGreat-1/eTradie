from __future__ import annotations

from datetime import datetime as dt, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BillingRepository:
    """Manages billing_usage table for tracking usage quotas."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_or_create_usage(self, user_id: str) -> dict:
        """Get the user's usage, creating a new row if none exists."""
        # Ensure we reset daily limits if last_reset_at was yesterday
        # We handle the day check in Python logic for simplicity
        stmt = text(
            \"\"\"
            INSERT INTO billing_usage (user_id) 
            VALUES (:user_id)
            ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
            RETURNING analyses_today, llm_tokens_used, execution_attempts, watcher_count, last_reset_at
            \"\"\"
        )
        res = await self._session.execute(stmt, {"user_id": user_id})
        row = res.mappings().first()
        await self._session.commit()
        return dict(row) if row else {}

    async def reset_daily_usage_if_needed(self, user_id: str):
        """Reset analyses_today if last_reset_at is not today."""
        usage = await self.get_or_create_usage(user_id)
        last_reset = usage.get("last_reset_at")
        
        if last_reset:
            now = dt.now(timezone.utc)
            # If the calendar day has changed
            if last_reset.date() != now.date():
                stmt = text(
                    \"\"\"
                    UPDATE billing_usage
                    SET analyses_today = 0, last_reset_at = NOW()
                    WHERE user_id = :user_id
                    """
                )
                await self._session.execute(stmt, {"user_id": user_id})
                await self._session.commit()

    async def increment_analysis(self, user_id: str):
        """Increment the analyses_today count and record the timestamp atomically."""
        stmt = text(
            """
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
            """
        )
        await self._session.execute(stmt, {"user_id": user_id})
        await self._session.commit()

    async def get_usage_for_user(self, user_id: str) -> dict:
        """Return the full usage row for a user (for the dashboard countdown)."""
        stmt = text(
            """
            SELECT analyses_today, llm_tokens_used, ta_cycles_used,
                   macro_cycles_used, execution_attempts, watcher_count,
                   last_analysis_at, last_reset_at
            FROM billing_usage
            WHERE user_id = :user_id
            """
        )
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
        stmt = text(
            """
            UPDATE billing_usage
            SET llm_tokens_used = llm_tokens_used + :tokens
            WHERE user_id = :user_id
            \"\"\"
        )
        await self._session.execute(stmt, {"user_id": user_id, "tokens": tokens})
        await self._session.commit()
    async def increment_usage_metric(self, user_id: str, column: str, amount: int = 1):
        \"\"\"Increment a specific usage metric column (e.g., ta_cycles_used).\"\"\"
        # Validate column name to prevent SQL injection
        allowed = {
            "ta_cycles_used", "macro_cycles_used", "execution_attempts", 
            "llm_tokens_used", "analyses_today", "watcher_count"
        }
        if column not in allowed:
            return

        stmt = text(
            f\"\"\"
            UPDATE billing_usage
            SET {column} = {column} + :amount
            WHERE user_id = :user_id
            \"\"\"
        )
        await self._session.execute(stmt, {"user_id": user_id, "amount": amount})
        await self._session.commit()
