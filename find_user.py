
import asyncio
from sqlalchemy import text
from app.db.engine import engine

async def find_user():
    async with engine.connect() as conn:
        print("Searching for users...")
        query = text("""
            SELECT id, tg_user_id, username, first_name 
            FROM users 
            WHERE first_name ILIKE :search
               OR username ILIKE :search
               OR CAST(tg_user_id AS TEXT) LIKE :search
        """)
        
        # Searching for 'Aleksey', 'Alex', or explicitly the log ID '632600126' seen earlier
        searches = ['%Алексей%', '%Alex%', '%632600126%']
        
        found = []
        for s in searches:
            res = await conn.execute(query, {"search": s})
            rows = res.fetchall()
            for r in rows:
                if r not in found:
                    found.append(r)
        
        for u in found:
            print(f"ID: {u.id}, TG: {u.tg_user_id}, User: {u.username}, Name: {u.first_name}")

if __name__ == "__main__":
    asyncio.run(find_user())
