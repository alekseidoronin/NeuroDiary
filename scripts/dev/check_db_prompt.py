
import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.db.models import BotSettings

async def check():
    async with async_session() as db:
        res = await db.execute(select(BotSettings).where(BotSettings.key == "system_prompt"))
        setting = res.scalar_one_or_none()
        if setting:
            print(f"FOUND IN DB: {setting.value[:100]}...")
            # Delete it so it uses the code version
            await db.delete(setting)
            await db.commit()
            print("DELETED DB OVERRIDE")
        else:
            print("NOT IN DB")

if __name__ == "__main__":
    asyncio.run(check())
