
import asyncio
import logging
from aiogram import Bot
from sqlalchemy import select
from app.config import settings
from app.db.engine import async_session
from app.db.models import JournalEntry, User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_history():
    # Initialize bot
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    user_uuid = "155175ec-b25c-4540-8deb-79e382d547cd"
    
    async with async_session() as db:
        # Get user
        user = await db.scalar(select(User).where(User.id == user_uuid))
        if not user:
            print("User not found")
            return

        # Get entries imported (input_type='import') or just all entries sorted by date
        # The user wants "all this diary for all days".
        # Let's fetch all entries for this user, sorted by date.
        
        result = await db.execute(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.entry_date)
        )
        entries = result.scalars().all()
        
        print(f"Found {len(entries)} entries. Sending to {user.tg_user_id}...")
        
        for entry in entries:
            text = entry.final_diary_text
            if not text:
                continue
                
            # Formatting checks? The text is already formatted.
            # Convert <br> to newlines if any, though the import usually has newlines.
            
            try:
                await bot.send_message(
                    chat_id=user.tg_user_id,
                    text=text,
                    parse_mode="HTML"
                )
                print(f"Sent entry for {entry.entry_date}")
                await asyncio.sleep(0.5) # Avoid flood limits
            except Exception as e:
                print(f"Failed to send entry {entry.entry_date}: {e}")
                
    await bot.session.close()
    print("Done sending history.")

if __name__ == "__main__":
    asyncio.run(send_history())
