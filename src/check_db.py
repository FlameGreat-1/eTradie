import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def check_db():
    url = os.getenv('DATABASE_URL')
    if not url:
        # Fallback to default local URL for the container
        url = "postgresql+asyncpg://etradie:etradie@postgres:5432/etradie"
    
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT trade_id, status, user_id FROM management_trades'))
        rows = res.fetchall()
        print('--- MANAGEMENT TRADES ---')
        for r in rows:
            print(dict(r._mapping))

        res2 = await conn.execute(text('SELECT event_type, status, user_id FROM execution_audit_logs'))
        rows2 = res2.fetchall()
        print('\n--- EXECUTION AUDIT LOGS ---')
        for r in rows2:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check_db())
