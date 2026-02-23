
import asyncio
from sqlalchemy import text
from app.db.engine import engine

async def make_admin():
    user_id = 632600126  # From logs
    async with engine.connect() as conn:
        # Check if user exists
        res = await conn.execute(text("SELECT id FROM users WHERE tg_user_id = :uid"), {"uid": user_id})
        row = res.fetchone()
        
        if row:
            print(f"User {user_id} found. Setting role to admin...")
            await conn.execute(text("UPDATE users SET role = 'admin' WHERE tg_user_id = :uid"), {"uid": user_id})
            await conn.commit()
            print("Done.")
        else:
            print(f"User {user_id} not found in DB yet. Creating...")
            # Create the user if not exists
            await conn.execute(text("""
                INSERT INTO users (tg_user_id, username, first_name, role, balance)
                VALUES (:uid, 'unknown', 'Admin', 'admin', 0)
            """), {"uid": user_id})
            await conn.commit()
            print("User created as admin.")

if __name__ == "__main__":
    asyncio.run(make_admin())
