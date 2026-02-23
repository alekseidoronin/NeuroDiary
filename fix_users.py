
import asyncio
from sqlalchemy import text
from app.db.engine import engine

async def fix():
    async with engine.connect() as conn:
        # Check users table
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"))
        columns = [r[0] for r in res]
        print(f"Columns in users: {columns}")
        
        if 'balance' not in columns:
            print("Adding balance to users...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN balance NUMERIC(10, 2) DEFAULT 0"))
        
        if 'referrer_id' not in columns:
            print("Adding referrer_id to users...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN referrer_id UUID REFERENCES users(id)"))

        if 'limit_overrides' not in columns:
            print("Adding limit_overrides to users...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN limit_overrides JSONB"))

        await conn.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(fix())
