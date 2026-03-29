import asyncio
from app.db.engine import async_session
from app.db.models import BotSettings
from sqlalchemy import select, update

async def run():
    async with async_session() as db:
        # Update specific model keys if they point to the old model
        await db.execute(
            update(BotSettings)
            .where(BotSettings.key == "llm_model", BotSettings.value == "gemini-2.0-flash")
            .values(value="gemini-1.5-flash")
        )
        await db.execute(
            update(BotSettings)
            .where(BotSettings.key == "gemini_model", BotSettings.value == "gemini-2.0-flash")
            .values(value="gemini-1.5-flash")
        )
        
        # Also, check if there are ANY entries in BotSettings
        res = await db.execute(select(BotSettings))
        settings = res.scalars().all()
        print(f"Current BotSettings count: {len(settings)}")
        for s in settings:
            print(f"{s.key}: {s.value}")
            
        await db.commit()
        print("Database update complete (if applicable).")

if __name__ == "__main__":
    asyncio.run(run())
