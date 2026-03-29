import asyncio
from app.db.engine import async_session
from app.db.models import BotSettings
from sqlalchemy import update, delete

async def fix():
    async with async_session() as db:
        # Update llm_model to the working one
        await db.execute(
            update(BotSettings)
            .where(BotSettings.key == "llm_model")
            .values(value="gemini-3-pro-preview")
        )
        print("Updated llm_model to gemini-3-pro-preview in DB")
        
        # Also ensure gemini_model isn't overriding
        await db.execute(
            update(BotSettings)
            .where(BotSettings.key == "gemini_model")
            .values(value="gemini-3-pro-preview")
        )
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(fix())
