import asyncio
from app.db.engine import async_session
from app.db.models import BotSettings
from sqlalchemy import select
from app.services.crypto import decrypt_value

async def check_settings():
    async with async_session() as db:
        res = await db.execute(select(BotSettings))
        settings = res.scalars().all()
        print(f"Found {len(settings)} settings")
        for s in settings:
            if s.is_secret:
                try:
                    val = decrypt_value(s.encrypted_value)
                    # Mask most of the key
                    masked = val[:4] + "..." + val[-4:] if len(val) > 8 else "***"
                    print(f"{s.key} (secret): {masked}")
                except Exception:
                    print(f"{s.key} (secret): <decrypt error>")
            else:
                print(f"{s.key}: {s.value}")

if __name__ == "__main__":
    asyncio.run(check_settings())
