
import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.db.models import BotSettings

async def check():
    async with async_session() as db:
        res = await db.execute(select(BotSettings).where(BotSettings.key == "user_template"))
        setting = res.scalar_one_or_none()
        if setting:
            print(f"FOUND USER TEMPLATE IN DB: {setting.value[:100]}...")
            await db.delete(setting)
            await db.commit()
            print("DELETED USER TEMPLATE DB OVERRIDE")
        else:
            print("USER TEMPLATE NOT IN DB")

if __name__ == "__main__":
    asyncio.run(check())
