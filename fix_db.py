
import asyncio
from sqlalchemy import text
from app.db.engine import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'journal_entries'"))
        columns = [r[0] for r in res]
        print(f"Columns in journal_entries: {columns}")
        
        if 'is_admin_entry' not in columns:
            print("Adding is_admin_entry column...")
            await conn.execute(text("ALTER TABLE journal_entries ADD COLUMN is_admin_entry BOOLEAN DEFAULT FALSE"))
            await conn.commit()
            print("Done.")
        else:
            print("Column exists.")

if __name__ == "__main__":
    asyncio.run(check())
